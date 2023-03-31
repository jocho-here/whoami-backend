from importlib.metadata import entry_points


def load_modules(app=None):
    for entry_point in entry_points()["routes"]:
        view_module = entry_point.load()

        if app:
            add_router = getattr(view_module, "add_router", None)

            if add_router:
                add_router(app)
