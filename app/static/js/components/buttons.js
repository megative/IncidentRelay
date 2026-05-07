function makeIconButton(options) {
    /*
     * Build an accessible icon-only button.
     *
     * Required:
     *   icon: Font Awesome class, for example "fas fa-edit"
     *   label: human-readable action label
     *
     * Optional:
     *   className: extra button classes
     *   onClick: click handler
     */
    const button = $("<button>")
        .attr("type", "button")
        .addClass("btn btn-icon btn-small")
        .attr("title", options.label)
        .attr("aria-label", options.label);

    if (options.className) {
        button.addClass(options.className);
    }

    button.append(
        $("<i>")
            .addClass(options.icon)
            .attr("aria-hidden", "true")
    );

    button.append(
        $("<span>")
            .addClass("sr-only")
            .text(options.label)
    );

    if (typeof options.onClick === "function") {
        button.on("click", options.onClick);
    }

    return button;
}
