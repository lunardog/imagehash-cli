import click
from PIL import Image
import imagehash as ih
import os

HASH_FUNCTIONS = {
    'average': ih.average_hash,
    'perception': ih.phash,
    'difference': ih.dhash,
    'wavelet': ih.whash
}


def get_new_name(orig_path, hash, template=None):
    """ Returns new file name, given hash """

    # get the path, name and extension
    base, ext = os.path.splitext(orig_path)
    path = os.path.dirname(base)
    name = os.path.basename(base)

    if template is None:
        template = os.path.join('{path}', '{hash}{ext}')

    new_name = template.format(path=path, hash=hash, ext=ext, name=name)

    return new_name


def get_hash(img, hash_type):
    """ Returns hash of the PIL image """
    if hash_type in HASH_FUNCTIONS:
        hash = str(HASH_FUNCTIONS[hash_type](img))
    else:
        raise click.UsageError('Unknown hash type: %s' % (hash_type))
    return str(hash)


@click.command()
@click.option(
    '--hash',
    type=click.Choice(HASH_FUNCTIONS.keys()),
    default='average'
)
@click.option('--rename', is_flag=True)
@click.option('--dry-run', is_flag=True)
@click.option(
    '--template',
    default=None,
    help='Template for rename (e.g. {path}/{hash}{ext})'
)
@click.argument('image',
                type=click.Path(exists=True),
                required=True)
def main(hash, rename, dry_run, template, image):
    """Command Line Image Hash"""
    orig_path = image

    try:
        img = Image.open(orig_path)
    except IOError:
        raise click.FileError(orig_path)

    hash_string = get_hash(img, hash)
    if rename:
        new_name = get_new_name(orig_path, hash_string, template)
        click.echo('%s -> %s' % (orig_path, new_name), err=True)
        if not dry_run:
            try:
                os.rename(orig_path, new_name)
            except OSError:
                raise click.FileError(new_name)
    else:
        click.echo(hash_string, nl=False)

    return hash_string
