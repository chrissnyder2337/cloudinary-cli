import click
from .utils import *
import cloudinary
from cloudinary import api, uploader, utils
from os import getcwd
import os
from json import dumps
from pathlib import Path

@click.group()
@click.option("-c", "--config")
def cli(config):
    if config:
        cloudinary._config._parse_cloudinary_url(config)
    pass

@click.command("upload")
@click.argument("imgstring")
@click.option("-pid", "--public_id")
@click.option("-type", "--_type", default="upload")
@click.option("-up", "--upload_preset")
@click.option("-t", "--transformation", help="A raw transformation (eg. f_auto,q_auto,w_500,e_vectorize")
@click.option("-e", "--eager", help="An eager transformation or an array of eager transformations")
@click.option("-o", "--options", help="Options to use (eg. -o option1=value1&option2=value2")
@click.option("-open", "--_open", is_flag=True)
def upload(imgstring, public_id, _type, upload_preset, transformation, eager, options, _open):
    if eager:
        eager = parse_option_value(eager)
    options = {k: v if k != "eager" else parse_option_value(v) for k,v in [x.split('=') for x in options.split('&')]} if options else {}
    res = uploader.upload(imgstring, public_id=public_id, type=_type, resource_type="auto", upload_preset=upload_preset, raw_transformation=transformation, eager=eager, **options)
    log(res)
    
    if _open:
        open_url(res['url'])

@click.command("search", help="""
Lucene query syntax search string
eg. cld search cat AND tags:kitten -f context -f tags -n 10
""")
@click.argument("query", nargs=-1)
@click.option("-f", "--with_field", multiple=True)
@click.option("-s", "--sort_by", nargs=2)
@click.option("-a", "--aggregate", nargs=1)
@click.option("-n", "--max_results", nargs=1, default=10)
def search(query, with_field, sort_by, aggregate, max_results):
    exp = cloudinary.Search().expression(" ".join(query))
    if with_field:
        for i in with_field:
            exp = exp.with_field(i)
    if sort_by:
        exp = exp.sort_by(*sort_by)
    if aggregate:
        exp = exp.aggregate(aggregate)
    res = exp.max_results(max_results).execute()
    log(res)

@click.command("admin", help="""
\b
format: cld admin <function> <parameters> <keyword_arguments>
\teg. cld admin resources max_results=10 tags=sample
""")
@click.argument("params", nargs=-1)
def admin(params):
    try:
        func = api.__dict__[params[0]]
        if not callable(func):
            raise Exception(f"{func} is not callable.")
            exit(1)
    except:
        print(f"Function {params[0]} does not exist in the Admin API.")
        exit(1)
    parameters, options = parse_args_kwargs(func, params[1:]) if len(params) > 1 else ([], {})
    res = func(*parameters, **options) 
    log(dumps(res, indent=2))


@click.command("uploader", help="""
\b
format: cld uploader <function> <parameters> <keyword_arguments>
\teg. cld uploader upload http://res.cloudinary.com/demo/image/upload/sample public_id=flowers
\t    cld uploader rename flowers secret_flowers to_type=private
""")
@click.argument("params", nargs=-1)
def _uploader(params):
    try:
        func = uploader.__dict__[params[0]]
    except:
        print(f"Function {params[0]} does not exist in the Upload API.")
        exit(1)
    if (callable(func)):
        print(params)
        parameters, options = parse_args_kwargs(func, params[1:]) if len(params) > 1 else ([], {})
        # print(parameters, options)
        res = func(*parameters, **options) 
        log(dumps(res, indent=2))

@click.command("fetch")
@click.argument("url", nargs=1)
@click.option("-t", "--transformation")
def fetch(args, transformation):
    res = utils.cloudinary_url(url, type="fetch", raw_transformation=transformation)[0]
    open_url(res)

@click.command("upload_dir")
@click.argument("directory", default=".")
@click.option("-t", "--transformation", help="Transformation to apply on all uploads")
@click.option("-f", "--folder", default="", help="Specify the folder you would like to upload resources to in Cloudinary")
@click.option("-p", "--preset", help="Upload preset to use")
@click.option("-v", "--verbose", is_flag=True)
@click.option("-vv", "--very_verbose", is_flag=True)
@click.option("-nr", "--non_recursive", is_flag=True) # Not implemented yet :)
def upload_dir(directory, transformation, folder, preset, verbose, very_verbose, non_recursive):
    items, skipped = [], []
    current_directory = os.path.abspath(directory)
    parent = os.path.dirname(current_directory)
    current_dir_abs_path = current_directory[len(parent)+1:]
    for root, _, files in os.walk(directory):
        for fi in files:
            file_path = os.path.abspath(os.path.join(current_directory, root, fi))
            full_path = file_path[len(parent) + 1:] if folder == "" else folder + "/" + file_path[len(parent) + 1:]
            if verbose or very_verbose:
                print(f"Uploading {file_path} as {full_path}... ", end="")
            pid = file_path[len(parent) + 1:]
            suffix = len(Path(pid).suffix)
            if suffix:
                pid = pid[:-suffix]
            try:
                _r = uploader.upload(file_path, public_id=f"{pid}", folder=folder, resource_type="auto", upload_preset=preset, raw_transformation=transformation)
                if verbose or very_verbose:
                    print("Success!")
            except Exception as e:
                if verbose or very_verbose:
                    print("Failed!")
                print(e)
            if very_verbose:
                log(_r)
            items.append(_r['public_id'])

    print(f"\n{len(items)} resources uploaded:")
    print('\n'.join(items))
    if len(skipped):
        print(f"\n{len(skipped)} items skipped:")
        print('\n'.join(skipped))

@click.command("url")
@click.argument("pid")
@click.argument("transformation", default="")
@click.option("-t", "--resource_type", default="image")
def url(pid, resource_type, transformation):
    res = utils.cloudinary_url(pid, resource_type=resource_type, raw_transformation=transformation)[0]
    print(res)
    open_url(res)

@click.command("ls", help="""
\b
List all resources by calling the Admin API multiple times
\tformat: cld ls <fields to return or resource search filters>
\teg. cld ls
\teg. Find all private resources and return the public_id
\t    cld ls type=private public_id
""")
@click.argument("fields_and_options", nargs=-1)
def ls(fields_and_options):
    fields, options = [], {}
    for x in fields_and_options:
        if "=" in x:
            tmp = x.split("=")
            options[tmp[0]] = tmp[1]
        else:
            fields.append(x)
    count = 0
    resources = []
    cursor = None
    while True:
        res = api.resources(max_results=500, next_cursor=cursor, **options)
        resources += res['resources']
        count += 1
        if 'cursor' in res.keys():
            cursor = res['cursor']
        else:
            break
    resources = list(map(lambda x: {key: x[key] for key in fields}, resources)) if len(fields) > 1 else list(map(lambda x: x[fields[0]], resources)) if len(fields) > 0 else resources
    log("[" + ",\n".join([dumps(x, indent=2) for x in resources]) + "]")
    print(f"API called {count} time(s).")
    print(f"{len(resources)} resources found.")


@click.command("make") # scaffolding
@click.argument("_type", nargs=-1)
def make(_type):
    language = "html"
    if _type[-1] in TEMPLATE_EXTS.keys():
        language = _type[-1]
        _type = _type[:-1]
    elif _type[0] in TEMPLATE_EXTS.keys():
        language = _type[0]
        _type = _type[1:]
    try:    
        print(load_template(language, '_'.join(_type)))
    except:
        print("Template not found.")

cli.add_command(upload)
cli.add_command(search)
cli.add_command(make)
cli.add_command(admin)
cli.add_command(_uploader)
cli.add_command(fetch)
cli.add_command(upload_dir)
cli.add_command(url)
cli.add_command(ls)

def main():
    cli()