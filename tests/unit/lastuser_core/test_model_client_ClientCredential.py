import funnel.models as models

from .test_db import TestDatabaseFixture


class TestClientCredential(TestDatabaseFixture):
    def setUp(self):
        """
        setUp for testing ClientCredential model
        """
        super(TestClientCredential, self).setUp()

    def test_clientcredential_new(self):
        """
        Test for ClientCredential model's new()
        """
        auth_client = self.fixtures.auth_client
        cred, secret = models.AuthClientCredential.new(auth_client)
        assert cred.auth_client == auth_client
        assert isinstance(cred, models.AuthClientCredential)
        client_secret = cred.secret_hash
        assert client_secret.startswith('sha256$')

    def test_clientcredential_get(self):
        """
        Test for ClientCredential model's get()
        """
        auth_client = self.fixtures.auth_client
        cred, secret = models.AuthClientCredential.new(auth_client)
        name = cred.name
        get_credentials = models.AuthClientCredential.get(name)
        assert isinstance(get_credentials, models.AuthClientCredential)
        assert cred == get_credentials

    def test_clientcredential_secret_is(self):
        """
        Test for checking if clientcredential's secret is a SHA256 string (64 characters) prepended with 'sha256$'
        """
        auth_client = self.fixtures.auth_client
        cred, secret = models.AuthClientCredential.new(auth_client)
        assert cred.secret_is(secret)
        assert len(secret) in (43, 44)
