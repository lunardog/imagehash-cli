import pytest
from click.testing import CliRunner
from imagehash_cli import cli
from PIL import Image
import os


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def image():
    img = Image.new('RGB', (255, 255))
    return img


def test_hash_functions():
    assert len(cli.HASH_FUNCTIONS) == 4


def test_get_hash(image):
    hash_functions = cli.HASH_FUNCTIONS
    for key in hash_functions:
        hash_function = hash_functions[key]
        hash = cli.get_hash(image, 'average')
        assert type(hash) == str
        assert hash == str(hash_function(image))
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
    result = runner.invoke(cli.main)
    assert result.exception


def test_cli_file(runner, image):
    filename = '/tmp/test.jpg'
    imghash = cli.get_hash(image, 'average')
    with runner.isolated_filesystem():
        image.save(filename, format='JPEG')
        result = runner.invoke(cli.main, [filename])
        assert result.exit_code == 0
        assert result.output == imghash


def test_cli_missing_file(runner, image):
    filename = '/tmp/test.jpg'
    if os.path.exists(filename):
        os.remove(filename)
    with runner.isolated_filesystem():
        result = runner.invoke(cli.main, [filename])
        assert result.exception


def test_cli_file_hash(runner, image):
    filename = '/tmp/test.jpg'
    hash_functions = cli.HASH_FUNCTIONS
    if os.path.exists(filename):
        os.remove(filename)
    with runner.isolated_filesystem():
        image.save(filename, format='JPEG')
        for h in hash_functions.keys():
            imghash = cli.get_hash(image, h)
            result = runner.invoke(cli.main, [filename, '--hash', h])
            assert result.exit_code == 0
            assert result.output == imghash


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
