import pytest

from plenum.common.version import (
    InvalidVersionError, VersionBase, GenericVersion,
    PEP440BasedVersion, SemVerBase, DigitDotVersion,
    SemVerReleaseVersion, PackageVersion
)


def abc_required(properties=None, classmethods=None):
    def _f(*_, **__):
        pass

    res = {}
    for p in properties or []:
        res[p] = property(_f)
    for clm in classmethods or []:
        res[clm] = classmethod(_f)
    return res


def iterate_abstracts(required, cls_name, base_cls, base_required=None):
    for i in range(len(required)):
        _dict = {
            attr: f for idx, (attr, f) in
            enumerate(required.items()) if idx <= i
        }
        if base_required:
            _dict.update(base_required)
        version_cls = type(cls_name, (base_cls,), _dict)
        yield (version_cls, i + 1 == len(required))


@pytest.fixture
def version_base_required():
    return abc_required(
        properties=('full', 'parts', 'release', 'release_parts'),
    )


# this test ensures that VersionBase declares specific
# set of abstracts that child classes must implement
def test_version_base_abstracts(version_base_required):
    for version_cls, filled in iterate_abstracts(
            version_base_required,
            'VersionBaseChild',
            VersionBase):
        if filled:
            version_cls('1.2.3')
        else:
            with pytest.raises(TypeError):
                version_cls('1.2.3')


def test_version_base_comparison_operators(version_base_required):

    def parse(self, val):
        try:
            return int(val)
        except ValueError:
            raise InvalidVersionError()

    version_base_required['_parse'] = parse

    version_cls = type("VersionBaseChild", (VersionBase,), version_base_required)

    assert version_cls('1') < version_cls('2')
    assert version_cls('2') > version_cls('1')
    assert version_cls('1') == version_cls('1')
    assert version_cls('1') <= version_cls('2')
    assert version_cls('2') <= version_cls('2')
    assert version_cls('2') >= version_cls('1')
    assert version_cls('1') >= version_cls('1')
    assert version_cls('1') != version_cls('2')


def test_version_base_init_with_spaces(version_base_required):
    version_cls = type("VersionBaseChild", (VersionBase,), version_base_required)
    for version in [' 1.2.3', '1.2.3 ', ' 1.2.3 ']:
        with pytest.raises(InvalidVersionError):
            version_cls(version)
        version_cls(version, allow_non_stripped=True)


def test_sem_ver_base_api(version_base_required):
    version_base_required['release_parts'] = property(
        lambda self: self._version.split('.'))
    version_cls = type("SemVerBaseChild", (SemVerBase,), version_base_required)
    assert version_cls('1.2.3').major == '1'
    assert version_cls('1.2.3').minor == '2'
    assert version_cls('1.2.3').patch == '3'


def test_generic_version_invalid():
    for version in [
        '1.@2.3',
        '1. 2.3',
        '1.2.3~'

    ]:
        with pytest.raises(InvalidVersionError):
            GenericVersion(version)


def test_generic_version_valid():
    GenericVersion('1.a.B-+!')


def test_generic_version_api():
    version = '1.2.3'
    assert GenericVersion(version).full == version
    assert GenericVersion(version).parts == (version,)
    assert GenericVersion(version).release == version
    assert GenericVersion(version).release_parts == (version,)


# TODO do we need more test coverage here ?
# (PEP440BasedVersion just wraps packaging package)

@pytest.mark.parametrize(
    'val1,val2,res',
    [
        ('1.2.3', '1.2.3.rc1', 1),
        ('1.2.3.dev2', '1.2.3.rc1', -1),
        ('1.2.3rc1', '1.2.3.rc1', 0),
    ]
)
def test_pep440_based_version_cmp(val1, val2, res):
    assert PEP440BasedVersion.cmp(
        PEP440BasedVersion(val1),
        PEP440BasedVersion(val2)
    ) == res


def test_pep440_based_version_public():
    assert PEP440BasedVersion('1.2.3rc1+1').public == '1.2.3rc1'


def test_pep440_based_version_full():
    assert PEP440BasedVersion('1!1.2.3').full == '1!1.2.3'
    assert PEP440BasedVersion('1.2.3.dev2').full == '1.2.3.dev2'
    assert PEP440BasedVersion('1.2.3.rc1').full == '1.2.3rc1'
    assert PEP440BasedVersion('1.2.3rc1').full == '1.2.3rc1'
    assert PEP440BasedVersion('1.2.3rc1+1').full == '1.2.3rc1+1'


def test_pep440_based_version_parts():
    assert PEP440BasedVersion('1.2.3.dev2').parts == (0, 1, 2, 3, 'dev', 2, None)
    assert PEP440BasedVersion('1!1.2.3.rc2').parts == (1, 1, 2, 3, 'rc', 2, None)
    assert PEP440BasedVersion('1.2.3+local').parts == (0, 1, 2, 3, 'local')


def test_pep440_based_version_release():
    assert PEP440BasedVersion('2!1.2.3.dev2').release == '1.2.3'


def test_pep440_based_version_release_parts():
    assert PEP440BasedVersion('1.2.3.dev2').release_parts == (1, 2, 3)


# valid PEP440:
#  devrelease
#  alpha prerelease
#  beta prerelease
#  rc prerelease
#  postrelease
#  epoch
#  local verion
@pytest.mark.parametrize(
    'version',
    [
        '1.2.3.dev2',
        '1.2.3a1',
        '1.2.3b2',
        '1.2.3rc3',
        '1.2.3.post1',
        '1!1.2.3',
        '1.2.3+1',
    ]
)
def test_digit_dot_version_invalid_value(version):
    with pytest.raises(InvalidVersionError):
        DigitDotVersion(version)


def test_digit_dot_version_parts():
    assert len(DigitDotVersion('1.2.3').parts) == 3


def test_digit_dot_version_valid():
    DigitDotVersion('1.2.3')
    DigitDotVersion('1.2.3', parts_num=3)
    DigitDotVersion('1.2.3', parts_num=[3, 4])
    DigitDotVersion('1.2.3.4.5', parts_num=(3, 5))


def test_digit_dot_version_invalid_parts_num():
    with pytest.raises(InvalidVersionError) as excinfo:
        DigitDotVersion('1.2.3', parts_num=4)
    assert 'should contain 4' in str(excinfo.value)

    with pytest.raises(InvalidVersionError) as excinfo:
        DigitDotVersion('1.2.3', parts_num=[4, 5])
    assert 'should contain 4 or 5' in str(excinfo.value)

    with pytest.raises(InvalidVersionError) as excinfo:
        DigitDotVersion('1.2.3', parts_num=(4, 6, 7))
    assert 'should contain 4 or 6 or 7' in str(excinfo.value)


# valid PEP440:
#  parts num != 3
# valid SemVer:
#  with prerelease part
#  with build metadata
@pytest.mark.parametrize(
    'version',
    [
        '1',
        '1.2',
        '1.2.3.4',
        '1.2.3-1',
        '1.2.3+1',
        '1.2.3-1+1',
    ]
)
def test_sem_ver_release_version_invalid(version):
    with pytest.raises(InvalidVersionError):
        SemVerReleaseVersion(version)


def test_sem_ver_release_version_valid():
    SemVerReleaseVersion('1.2.3')


def test_package_version_abstracts(version_base_required):
    package_version_required = abc_required(properties=('upstream',))

    for version_cls, filled in iterate_abstracts(
            package_version_required,
            'PackageVersionChild',
            PackageVersion,
            base_required=version_base_required):
        if filled:
            version_cls('1.2.3')
        else:
            with pytest.raises(TypeError):
                version_cls('1.2.3')
