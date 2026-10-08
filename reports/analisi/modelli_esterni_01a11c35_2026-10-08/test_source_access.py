"""Regress cross-account private native mounts before quota is consumed."""
import unittest
from source_access_preflight import admissible

class AccessTests(unittest.TestCase):
    def test_private_source_of_other_owner_is_not_native(self):
        self.assertFalse(admissible('davidmaisterx','davideferrante11/joint',True))
        self.assertTrue(admissible('davideferrante11','davideferrante11/joint',True))
        self.assertTrue(admissible('davidmaisterx','davideferrante11/joint',False))
        self.assertFalse(admissible('davidmaisterx','davideferrante11/joint',None))

if __name__=='__main__':unittest.main()
