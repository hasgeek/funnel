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
        assert client_secret.startswith('blake2b$')

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

    def test_clientcredential_upgrade_hash(self):
        """
        Test for transparent upgrade of client credential hash type
        """
        secret = 'D2axSjtbbWDkRFmSDXGpNSB9ypfqE1ekYD3YP37J85yJ'
        secret_sha256 = (
            'sha256$45c879362ed45b3f92a7ea3c1e53ecab0dd79c61cb357e6eb0de6d64408ea25c'
        )
        secret_blake2b = 'blake2b$3fe1e91bef5ded2648549349d72ed0f00a2a237a742b46e129f7b259a3288d7183e94d156f549c2f297485600351ca056da4671d989e0cbb7d4dedd31df2d322'
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
