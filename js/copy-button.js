// walk through all div.codehilite
// and add a copy button to each of them
for (const ch of document.querySelectorAll("div.codehilite")) {
	// the copy button can be found anywhere in the ui.shadcn website
	// ex: https://ui.shadcn.com/docs/theming
	const button = document.createElement("button");
	button.setAttribute(
		"class",
		"inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50 bg-transparent absolute top-3 right-2 z-10 size-7 hover:opacity-100 focus-visible:opacity-100",
	);

	const span = document.createElement("span");
	span.setAttribute("class", "sr-only");
	span.innerText = "Copy";
	button.appendChild(span);

	const icon = clipboardIcon();
	button.appendChild(icon);
	button.onclick = onCodeCopy;
	ch.appendChild(button);
}
