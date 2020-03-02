from click import command, argument

from cloudinary_cli.defaults import TEMPLATE_EXTS, logger
from cloudinary_cli.utils import load_template


@command("make", short_help="Scaffold Cloudinary templates.",
         help="""\b
Scaffold Cloudinary templates.
eg. cld make product gallery
""")
@argument("template", nargs=-1)
def make(template):
    language = "html"
    if template[-1] in TEMPLATE_EXTS.keys():
        language = template[-1]
        template = template[:-1]
    elif template[0] in TEMPLATE_EXTS.keys():
        language = template[0]
        template = template[1:]
    try:
        src = load_template(language, '_'.join(template))
        print(src)
    except Exception as e:
        logger.error(e)
