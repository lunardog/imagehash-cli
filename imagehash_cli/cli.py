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


def get_hash(img, hash_type='average'):
    """ Returns hash of the PIL image """
    if hash_type in HASH_FUNCTIONS:
        hash = str(HASH_FUNCTIONS[hash_type](img))
    else:
        raise click.UsageError('Unknown hash type: %s' % (hash_type))
    return str(hash)


def process_file(orig_path, hash, rename, template, dry_run):
    """ Process a single file """
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

    return hash_string


@click.command()
@click.pass_context
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
@click.argument(
    'image',
    type=click.Path(exists=True),
    nargs=-1,
    required=True
)
def main(ctx, hash, rename, dry_run, template, image):
    """Command Line Image Hash"""

    if len(image) == 1:
        # if one image provided, read it
        orig_path = image[0]
        response = process_file(orig_path, hash, rename, template, dry_run)
        if not rename:
            click.echo(response)
        return

    else:
        # if multiple images provided, go one by one
        responses = []
        for path in image:
            file_hash = process_file(path, hash, rename, template, dry_run)
            responses.append('%s %s' % (path, file_hash))
        response = os.linesep.join(responses)
        if not rename:
            click.echo(response)
        return response
