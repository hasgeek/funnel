import funnel.models as models

from .test_db import TestDatabaseFixture


class TestClientCredential(TestDatabaseFixture):
    def test_clientcredential_new(self):
        """Test for ClientCredential model's new()."""
        auth_client = self.fixtures.auth_client
        cred, _secret = models.AuthClientCredential.new(auth_client)
        assert cred.auth_client == auth_client
        assert isinstance(cred, models.AuthClientCredential)
        client_secret = cred.secret_hash
        assert client_secret.startswith('blake2b$32$')

    def test_clientcredential_get(self):
        """Test for ClientCredential model's get()."""
        auth_client = self.fixtures.auth_client
        cred, _secret = models.AuthClientCredential.new(auth_client)
        name = cred.name
        get_credentials = models.AuthClientCredential.get(name)
        assert isinstance(get_credentials, models.AuthClientCredential)
        assert cred == get_credentials

    def test_clientcredential_secret_is(self):
        """Test for checking if clientcredential's secret is valid."""
        auth_client = self.fixtures.auth_client
        cred, secret = models.AuthClientCredential.new(auth_client)
        assert cred.secret_is(secret)
        assert len(secret) in (43, 44)

    def test_clientcredential_upgrade_hash(self):
        """Test for transparent upgrade of client credential hash type."""
        secret = 'D2axSjtbbWDkRFmSDXGpNSB9ypfqE1ekYD3YP37J85yJ'
        secret_sha256 = (
            'sha256$45c879362ed45b3f92a7ea3c1e53ecab0dd79c61cb357e6eb0de6d64408ea25c'
        )
        secret_blake2b = 'blake2b$32$e7b49edf2b7c3945631d229dae3db30517f75047ce547a97ae27e9b46f69723a'
        cred = models.AuthClientCredential(
            auth_client=self.fixtures.auth_client, secret_hash=secret_sha256
        )
        assert cred.secret_hash == secret_sha256
        assert cred.secret_is('incorrect') is False
        assert cred.secret_hash == secret_sha256
        assert cred.secret_is('incorrect', upgrade_hash=True) is False
        assert cred.secret_hash == secret_sha256
        assert cred.secret_is(secret) is True
        assert cred.secret_hash == secret_sha256
        assert cred.secret_is(secret, upgrade_hash=True) is True
        assert cred.secret_hash != secret_sha256
        assert cred.secret_hash == secret_blake2b
