import sghi.app
from sghi.config import Config, ConfigProxy
from sghi.utils import ensure_instance_of, type_fqn


def setup(conf: Config) -> None:
    ensure_instance_of(
        value=conf,
        klass=Config,
        message=f"'conf' MUST be an instance of '{type_fqn(Config)}'.",
    )
    match sghi.app.conf:
        case ConfigProxy():
            sghi.app.conf.set_source(conf)
        case _:
            setattr(sghi.app, "conf", conf)  # noqa: B010       case _:
