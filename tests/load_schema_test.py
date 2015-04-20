import mock
import pytest

from pyramid_swagger import load_schema


@pytest.fixture
def mock_validator():
    return mock.Mock(spec=['validate', 'is_type'])


def test_required_validator_bool_is_missing():
    schema = {'paramType': 'body', 'name': 'body'}
    errors = list(load_schema.required_validator(None, True, {}, schema))
    assert len(errors) == 1
    assert 'body is required' in str(errors[0])


def test_required_validator_bool_is_present():
    schema = {'paramType': 'body', 'name': 'body'}
    inst = {'foo': 1}
    errors = list(load_schema.required_validator(None, True, inst, schema))
    assert len(errors) == 0


def test_required_validator_bool_not_required():
    schema = {'paramType': 'body', 'name': 'body'}
    errors = list(load_schema.required_validator(None, False, {}, schema))
    assert len(errors) == 0


def test_required_validator_list(mock_validator):
    required = ['one', 'two']
    errors = list(load_schema.required_validator(
        mock_validator, required, {}, {}))
    assert len(errors) == 2
