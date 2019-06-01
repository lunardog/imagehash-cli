from __future__ import print_function
import pytest
import click
from click.testing import CliRunner
from imagehash_cli import cli
from PIL import Image
import random
import os


try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def _simprint(s):
    """ Do to a string the same processing that print would do.

    Needed to compare expected outputs from the cli when they contain newlines
    or tabs. This is surprisingly difficult to do in a way that works on all
    Pythons. On 2, requires the print function from __future__.
    """
    buf = StringIO()
    print(s, file=buf)
    buf.flush()
    return buf.getvalue()


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def image():
    # TODO: not good to introduce random numbers in test
    # but it saves us from all black images
    color = (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )
    img = Image.new('RGB', (255, 255), color=color)
    return img


def test_hash_functions():
    assert len(cli.HASH_FUNCTIONS) == 4


def test_get_hash(image):
    hash_functions = cli.HASH_FUNCTIONS
    for key in hash_functions:
        hash_function = hash_functions[key]
        hash = cli.get_hash(image, key)
        assert type(hash) == str
        assert hash == str(hash_function(image))
    try:
        hash = cli.get_hash(image, 'FOOBAR')
        assert False, 'Unknown hash type should raise an exception'
    except click.UsageError:
        pass


def test_get_new_name():
    samples = {
        './file.jpg': './HASH.jpg',
        '/path/file.jpg': '/path/HASH.jpg',
        '~/file.with.many.dots': '~/HASH.dots',
        '/foo/noextension': '/foo/HASH'
    }
    for filename in samples:
        expected_new_name = samples[filename]
        new_name = cli.get_new_name(filename, 'HASH')
        assert new_name == expected_new_name


def test_rename_with_template():
    oldname = '/foo/bar/path/file.name.ext'
    templates = {
        '{path}/{name}{ext}': '/foo/bar/path/file.name.ext',
        '{path}/{hash}{ext}': '/foo/bar/path/HASH.ext',
        '/tmp/{hash}{ext}': '/tmp/HASH.ext',
        '/tmp/{name}-{hash}.jpg': '/tmp/file.name-HASH.jpg',
        None: '/foo/bar/path/HASH.ext'
    }
    for template in templates:
        expected_new_name = templates[template]
        new_name = cli.get_new_name(oldname, 'HASH', template)
        assert new_name == expected_new_name


def test_cli(runner):
    # Executed, but no stream
    result = runner.invoke(cli.main)
    assert result.exception


def test_cli_no_image(runner):
    # Executed, but no stream
    result = runner.invoke(cli.main, [])
    assert result.exception


def test_cli_file(runner, image):
    filename = '/tmp/test.jpg'
    imghash = cli.get_hash(image, 'average')
    with runner.isolated_filesystem():
        image.save(filename, format='JPEG')
        result = runner.invoke(cli.main, [filename])
        assert result.exit_code == 0
        expected_output = _simprint("%s\t%s" % (imghash, filename))
        assert result.output == expected_output
        os.remove(filename)


def test_cli_not_image_file(runner):
    filename = '/tmp/test.jpg'
    # try again with an empty file
    with runner.isolated_filesystem():
        open(filename, 'a').close()
    with runner.isolated_filesystem():
        open(filename, 'a').close()
        result = runner.invoke(cli.main, [filename])
        assert result.exception
        os.remove(filename)


def test_cli_missing_file(runner):
    filename = '/tmp/test.jpg'
    with runner.isolated_filesystem():
        if os.path.exists(filename):
            os.remove(filename)
        result = runner.invoke(cli.main, [filename])
        assert result.exception


def test_cli_multiple(runner, image):
    num_images = 5
    filenames = ['/tmp/test-%d.jpg' % (n) for n in range(num_images)]
    imghash = cli.get_hash(image)
    with runner.isolated_filesystem():
        for path in filenames:
            if os.path.exists(path):
                os.remove(path)
            image.save(path, format='JPEG')
        result = runner.invoke(cli.main, filenames)
        assert result.exit_code == 0
        expected_lines = ['%s\t%s' % (imghash, path) for path in filenames]
        expected_output = _simprint(os.linesep.join(expected_lines))
        assert result.output == expected_output
        # clean up
        for path in filenames:
            os.remove(path)


def test_cli_multiple_rename(runner, image):
    num_images = 5
    filenames = ['/tmp/test-%d.jpg' % (n) for n in range(num_images)]
    imghash = cli.get_hash(image)
    with runner.isolated_filesystem():
        for path in filenames:
            if os.path.exists(path):
                os.remove(path)
            image.save(path, format='JPEG')
        result = runner.invoke(cli.main, filenames+['--rename'])
        assert result.exit_code == 0
        for path in filenames:
            new_name = cli.get_new_name(path, imghash)
            assert os.path.exists(new_name)
            assert not os.path.exists(path)
        # clean up
        for path in filenames:
            new_name = cli.get_new_name(path, imghash)
            # hashes might be the same
            if os.path.exists(new_name):
                os.remove(new_name)


def test_cli_file_rename(runner, image):
    filename = '/tmp/test.jpg'
    imghash = cli.get_hash(image, 'average')
    new_name = cli.get_new_name(filename, imghash)
    with runner.isolated_filesystem():
        if os.path.exists(new_name):
            os.remove(new_name)
        image.save(filename, format='JPEG')
        result = runner.invoke(cli.main, [filename, '--rename'])
        assert result.exit_code == 0
        assert os.path.exists(new_name)
        # clean up th new file
        os.remove(new_name)


def test_cli_file_rename_template(runner, image):
    filename = '/tmp/test.jpg'
    imghash = cli.get_hash(image, 'average')
    template = '{path}/FOOBAR-{name}-{hash}{ext}'
    new_name = cli.get_new_name(filename, imghash, template)
    with runner.isolated_filesystem():
        if os.path.exists(new_name):
            os.remove(new_name)
        image.save(filename, format='JPEG')
        result = runner.invoke(
            cli.main,
            [filename, '--rename', '--template', template]
        )
        assert result.exit_code == 0
        assert os.path.exists(new_name)
        # clean up the new file
        os.remove(new_name)


def test_cli_file_rename_bad_filename(runner, image):
    filename = '/tmp/test.jpg'
    imghash = cli.get_hash(image, 'average')
    template = '/tmp/test.jpg/not_a_directory'
    new_name = cli.get_new_name(filename, imghash, template)
    with runner.isolated_filesystem():
        if os.path.exists(new_name):
            os.remove(new_name)
        image.save(filename, format='JPEG')
        result = runner.invoke(
            cli.main,
            [filename, '--rename', '--template', template]
        )
        assert result.exception
        assert not os.path.exists(new_name)


def test_cli_file_rename_dry_run(runner, image):
    filename = '/tmp/test.jpg'
    imghash = cli.get_hash(image, 'average')
    new_name = cli.get_new_name(filename, imghash)
    with runner.isolated_filesystem():
        if os.path.exists(new_name):
            os.remove(new_name)
        image.save(filename, format='JPEG')
        result = runner.invoke(cli.main, [filename, '--rename', '--dry-run'])
        assert result.exit_code == 0
        assert not os.path.exists(new_name)
