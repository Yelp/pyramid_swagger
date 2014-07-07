import jsonschema.exceptions
from pkg_resources import resource_filename
from jsonschema.validators import RefResolver
import simplejson
import jsonschema


def test_spec_validation_on_sample_spec():
    with open('tests/small_spec.json') as f:
        spec = simplejson.load(f)

    api_spec_path = resource_filename(
        'pyramid_swagger',
        'swagger_spec_schemas/v1.2/apiDeclaration.json'
    )
    with open(api_spec_path) as f:
        to_validate = simplejson.loads(f.read())
        resolver = RefResolver(
            "file://{0}".format(api_spec_path),
            to_validate
        )
        jsonschema.validate(spec, to_validate, resolver=resolver)
