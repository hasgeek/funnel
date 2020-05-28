from funnel.views.helpers import get_registration_text


class TestHelpers:
    def test_registration_text(self):
        # Zero
        assert (
            get_registration_text(count=0, registered=False)
            == "Be the first one to register!"
        )
        # One
        assert (
            get_registration_text(count=1, registered=True) == "You are now registered"
        )
        assert (
            get_registration_text(count=1, registered=False)
            == "One registration so far. Be the next one to register?"
        )
        # Less than ten
        assert (
            get_registration_text(count=5, registered=True)
            == "You and four others are now registered"
        )
        assert (
            get_registration_text(count=5, registered=False)
            == "Five registrations so far. Be the next one to register?"
        )
        # More than ten
        assert (
            get_registration_text(count=33, registered=True)
            == "You and 32 others are now registered"
        )
        assert (
            get_registration_text(count=3209, registered=False)
            == "3209 registrations so far. Be the next one to register?"
        )
