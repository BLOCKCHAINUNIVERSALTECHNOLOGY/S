// sdx.ui — Android UI toolkit (stub)
// Real implementation will bridge to Android Views / Compose

fn screen(title: str): str {
    print "[SDX] screen:", title
    ret title
}

fn button(label: str): str {
    print "[SDX] button:", label
    ret label
}

fn text(content: str): str {
    print "[SDX] text:", content
    ret content
}

fn show(msg: str): str {
    print "[SDX] show dialog:", msg
    ret msg
}

fn column(children: str): str {
    print "[SDX] column layout"
    ret children
}

fn row(children: str): str {
    print "[SDX] row layout"
    ret children
}
