const onSearchBarClick = (event) => {
	const dialog = document.getElementById("search-dialog");
	if (dialog) {
		dialog.showModal();
	}
};

const closeDialogFactory = (targetID, event) => {
	const dialog = document.getElementById(targetID);
	if (dialog && event.target === dialog) {
		dialog.close();
	}
};

const onSearchDialogClick = (event) => {
	return closeDialogFactory("search-dialog", event);
};

const onInputHandler = (event) => {
	const query = event.target.value;
	if (window.debounceTimer) {
		clearTimeout(debounceTimer);
	}
	window.debounceTimer = setTimeout(() => {
		if (searchWorker && query.length > 2) {
			console.log(`Posting message { "query": "${query}" }`);
			// https://lunrjs.com/guides/searching.html
			// we should append a wilcard and also a boost on exact term
			const lunrQuery = `${query}^10 ${query}* ${query}~1`;
			searchWorker.postMessage({ query: lunrQuery });
		} else if (query.length > 2) {
			console.warn("searchWorker is not defined");
		} else {
			const results = document.getElementById("mkdocs-search-results");
			if (results) {
				while (results.firstChild) {
					results.removeChild(results.firstChild);
				}
			}
		}
	}, 300);
};

const searchShortcutHandler = (event) => {
	if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
		event.preventDefault(); // Prevents default browser behavior (e.g., search bar in some apps)
		const dialog = document.getElementById("search-dialog");
		if (dialog) {
			dialog.showModal();
		}
	}
};

const updatePygmentsStylesheet = () => {
	const root = document.documentElement;
	const lightLink = document.getElementById("pygments-light");
	const darkLink = document.getElementById("pygments-dark");
	if (root.classList.contains("dark")) {
		if (darkLink && lightLink) {
			darkLink.media = "all";
			lightLink.media = "none";
		}
	} else {
		if (darkLink && lightLink) {
			darkLink.media = "none";
			lightLink.media = "all";
		}
	}
};

const onThemeSwitch = (event) => {
	const root = document.documentElement;
	root.classList.toggle("dark");
	if (root.classList.contains("dark")) {
		localStorage.setItem("theme", "dark");
	} else {
		localStorage.setItem("theme", "light");
	}

	updatePygmentsStylesheet();
};

const onBottomSidebarDialogClick = (event) => {
	const dialog = document.getElementById("bottom-sidebar");
	if (dialog && event.target === dialog) {
		dialog.close();
		const button = document.getElementById("menu-button");
		if (button) {
			button.dataset.state = "closed";
		}
	}
};

const onMobileMenuButtonClick = (event) => {
	event.currentTarget.dataset.state =
		event.target.dataset.state === "open" ? "closed" : "open";
	const dialog = document.getElementById("bottom-sidebar");
	if (dialog) {
		dialog.showModal();
	}
};

const clipboardIcon = () => {
	const svgElement = document.createElementNS(
		"http://www.w3.org/2000/svg",
		"svg",
	);
	svgElement.setAttribute("xmlns", "http://www.w3.org/2000/svg");
	svgElement.setAttribute("width", "24");
	svgElement.setAttribute("height", "24");
	svgElement.setAttribute("viewBox", "0 0 24 24");
	svgElement.setAttribute("fill", "none");
	svgElement.setAttribute("stroke", "currentColor");
	svgElement.setAttribute("stroke-width", "2");
	svgElement.setAttribute("stroke-linecap", "round");
	svgElement.setAttribute("stroke-linejoin", "round");
	svgElement.setAttribute(
		"class",
		"lucide lucide-clipboard-icon lucide-clipboard",
	);

	const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
	rect.setAttribute("width", "8");
	rect.setAttribute("height", "4");
	rect.setAttribute("x", "8");
	rect.setAttribute("y", "2");
	rect.setAttribute("rx", "1");
	rect.setAttribute("ry", "1");
	svgElement.appendChild(rect);

	const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
	path.setAttribute(
		"d",
		"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2",
	);
	svgElement.appendChild(path);

	return svgElement;
};

const checkIcon = () => {
	const svgElement = document.createElementNS(
		"http://www.w3.org/2000/svg",
		"svg",
	);
	svgElement.setAttribute("xmlns", "http://www.w3.org/2000/svg");
	svgElement.setAttribute("width", "24");
	svgElement.setAttribute("height", "24");
	svgElement.setAttribute("viewBox", "0 0 24 24");
	svgElement.setAttribute("fill", "none");
	svgElement.setAttribute("stroke", "currentColor");
	svgElement.setAttribute("stroke-width", "2");
	svgElement.setAttribute("stroke-linecap", "round");
	svgElement.setAttribute("stroke-linejoin", "round");
	svgElement.setAttribute("class", "lucide lucide-check-icon lucide-check");

	const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
	path.setAttribute("d", "M20 6 9 17l-5-5");
	svgElement.appendChild(path);

	return svgElement;
};

const onCodeCopy = (event) => {
	const button = event.target;
	const code = button.parentElement.querySelector("code");
	if (code) {
		const text = code.innerText;
		navigator.clipboard.writeText(text).then(
			// change the inner icon of the button (inline svg)
			() => {
				const svg = button.querySelector("svg");
				if (svg) {
					button.removeChild(svg);
					const check = checkIcon();
					button.appendChild(check);
					// reset the icon after few seconds
					setTimeout(() => {
						button.removeChild(check);
						const resetSvg = clipboardIcon();
						button.appendChild(resetSvg);
					}, 2000);
				}
			},
		);
	}
};

const toggleLayout = (event) => {
	if (document.documentElement.classList.contains("layout-fixed")) {
		document.documentElement.classList.remove("layout-fixed");
		document.documentElement.classList.add("layout-full");
		localStorage.setItem("html-layout", "layout-full");
	} else {
		document.documentElement.classList.remove("layout-full");
		document.documentElement.classList.add("layout-fixed");
		localStorage.setItem("html-layout", "layout-fixed");
	}
};

const fetchStargazers = (repoUrl) => {
	const span = document.getElementById("stargazers");
	if (span) {
		const chunks = repoUrl.split("/");
		if (chunks.length > 2) {
			const repo = chunks[chunks.length - 1];
			const owner = chunks[chunks.length - 2];
			const url = `https://api.github.com/repos/${owner}/${repo}`;
			fetch(url)
				.catch((error) => {
					console.error(`Error fetching stargazers at ${owner}:`, error);
				})
				.then((response) => response.json())
				.then((data) => {
					span.textContent = data.stargazers_count;
					console.log("Stargazers updated");
				});
		}
	}
};
