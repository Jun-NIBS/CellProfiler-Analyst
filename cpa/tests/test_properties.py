import os.path
import cpa

def test_old_filter():
    fn = os.path.join(os.path.dirname(__file__),
                      'test_properties_old_filter.properties')
    cpa.properties.LoadFile(fn)

