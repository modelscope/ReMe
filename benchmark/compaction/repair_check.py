"""Run generated payment fixes with a deliberately restricted Python grammar."""

import ast
from types import SimpleNamespace


class PaymentError(Exception):
    """A non-timeout provider error carrying an HTTP status."""

    status_code = 422


def repair_checks(source):  # pylint: disable=too-many-return-statements
    """Reject general Python programs; allow only a bounded retry function and inert clients."""
    names = ("success", "timeout_then_success", "http_402", "http_422", "exhaustion", "distinct_payments")
    failed = dict.fromkeys(names, False)
    try:
        tree = ast.parse(source)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        if len(functions) != 1 or functions[0].name != "charge_with_retry":
            return failed
        for node in tree.body:
            if node is functions[0]:
                continue
            if not isinstance(node, ast.Import) or any(alias.name != "uuid" for alias in node.names):
                return failed
        allowed_calls = {"range", "str", "TimeoutError", "uuid.uuid4", "client.charge"}
        allowed_nodes = (
            ast.FunctionDef,
            ast.arguments,
            ast.arg,
            ast.Constant,
            ast.Name,
            ast.Load,
            ast.Store,
            ast.Assign,
            ast.For,
            ast.Call,
            ast.Attribute,
            ast.keyword,
            ast.Try,
            ast.ExceptHandler,
            ast.Return,
            ast.Raise,
            ast.If,
            ast.Compare,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.BinOp,
            ast.Sub,
            ast.Pass,
            ast.Expr,
        )
        for node in ast.walk(functions[0]):
            if not isinstance(node, allowed_nodes):
                return failed
            if isinstance(node, ast.FunctionDef) and node is not functions[0]:
                return failed
            if isinstance(node, ast.Constant) and (
                isinstance(node.value, str)
                and len(node.value) > 100
                or isinstance(node.value, int)
                and abs(node.value) > 10
            ):
                return failed
            if isinstance(node, ast.Attribute) and ast.unparse(node) not in {"uuid.uuid4", "client.charge"}:
                return failed
            if isinstance(node, ast.Call) and ast.unparse(node.func) not in allowed_calls:
                return failed
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                return failed
        if functions[0].decorator_list or functions[0].returns or any(a.annotation for a in functions[0].args.args):
            return failed
        # No executable defaults, annotations or decorators in the accepted grammar.
        if any(not isinstance(node, ast.Constant) for node in functions[0].args.defaults):
            return failed
        if functions[0].args.kwonlyargs or functions[0].args.vararg or functions[0].args.kwarg:
            return failed
        if any(arg.annotation for arg in ast.walk(functions[0]) if isinstance(arg, ast.arg)):
            return failed
        if sum(isinstance(node, ast.For) for node in ast.walk(functions[0])) > 1:
            return failed
        serial = iter(range(1000))

        def bounded_range(*args):
            result = range(*args)
            if len(result) > 10:
                raise ValueError("Retry range exceeds test limit")
            return result

        namespace = {
            "__builtins__": {},
            "range": bounded_range,
            "str": str,
            "TimeoutError": TimeoutError,
            "uuid": SimpleNamespace(uuid4=lambda: f"test-key-{next(serial)}"),
        }
        module = ast.Module(body=functions, type_ignores=[])
        exec(compile(module, "<payment-fix>", "exec"), namespace)  # pylint: disable=exec-used
        fix = namespace["charge_with_retry"]

        def attempt(events, expected_calls, error=None):
            keys = []
            remaining = iter(events)

            def charge(invoice, idempotency_key):
                if invoice != "test-invoice":
                    raise AssertionError("Invoice was changed")
                keys.append(idempotency_key)
                event = next(remaining)
                if isinstance(event, Exception):
                    raise event
                return event

            try:
                result = fix(SimpleNamespace(charge=charge), "test-invoice")
                correct = error is None and result == "ok"
            except Exception as exc:
                correct = error is not None and exc is error
            return correct and len(keys) == expected_calls and len(set(keys)) == 1, keys

        result = {}
        result["success"], first = attempt(["ok"], 1)
        result["timeout_then_success"], _ = attempt([TimeoutError(), "ok"], 2)
        for status in (402, 422):
            error = PaymentError()
            error.status_code = status
            result[f"http_{status}"], _ = attempt([error, "ok"], 1, error)
        errors = [TimeoutError() for _ in range(3)]
        result["exhaustion"], _ = attempt(errors, 3, errors[-1])
        success, second = attempt(["ok"], 1)
        result["distinct_payments"] = success and result["success"] and first != second
        return result
    except Exception:
        return failed
