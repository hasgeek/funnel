import pytest

import funnel.models as models

from .test_db import TestDatabaseFixture


class TestOrganization(TestDatabaseFixture):
    def test_organization_init(self):
        """Test for initializing a Organization instance."""
        name = 'dachshunited'
        title = 'Dachshunds United'
        dachsunited = models.Organization(
            name=name, title=title, owner=self.fixtures.crusoe
        )
        assert isinstance(dachsunited, models.Organization)
        assert dachsunited.title == title
        assert dachsunited.name == name

    def test_organization_get(self):
        """Test for retrieving an organization."""
        name = 'spew'
        title = 'S.P.E.W'
        spew = models.Organization(name=name, title=title, owner=self.fixtures.crusoe)
        self.db_session.add(spew)
        self.db_session.commit()
        # scenario 1: when neither name or buid are passed
        with pytest.raises(TypeError):
            models.Organization.get()
        # scenario 2: when buid is passed
        buid = spew.buid
        get_by_buid = models.Organization.get(buid=buid)
        assert isinstance(get_by_buid, models.Organization)
        assert title == get_by_buid.title
        # scenario 3: when username is passed
        get_by_name = models.Organization.get(name=name)
        assert isinstance(get_by_name, models.Organization)
        assert title == get_by_name.title
        # scenario 4: when defercols is set to True
        get_by_name_with_defercols = models.Organization.get(name=name, defercols=True)
        assert isinstance(get_by_name_with_defercols, models.Organization)
        assert title == get_by_name_with_defercols.title

    def test_organization_all(self):
        """Test for getting all organizations (takes buid or name optionally)."""
        gryffindor = models.Organization(name='gryffindor', owner=self.fixtures.crusoe)
        ravenclaw = models.Organization(name='ravenclaw', owner=self.fixtures.crusoe)
        self.db_session.add(gryffindor)
        self.db_session.add(ravenclaw)
        self.db_session.commit()
        # scenario 1: when neither buids nor names are given
        assert models.Organization.all() == []
        # scenario 2: when buids are passed
        orglist = {gryffindor, ravenclaw}
        all_by_buids = models.Organization.all(buids=[_org.buid for _org in orglist])
        assert set(all_by_buids) == orglist
        # scenario 3: when org names are passed
        all_by_names = models.Organization.all(names=[_org.name for _org in orglist])
        assert set(all_by_names) == orglist
        # scenario 4: when defercols is set to True for names
        all_by_names_with_defercols = models.Organization.all(
            names=[_org.name for _org in orglist]
        )
        assert set(all_by_names_with_defercols) == orglist
        # scenario 5: when defercols is set to True for buids
        all_by_buids_with_defercols = models.Organization.all(
            buids=[_org.buid for _org in orglist]
        )
        assert set(all_by_buids_with_defercols) == orglist

    def test_organization_pickername(self):
        """Test for checking Organization's pickername."""
        # scenario 1: when only title is given
        abnegation = models.Organization(
            title="Abnegation", name='abnegation', owner=self.fixtures.crusoe
        )
        assert isinstance(abnegation.pickername, str)
        assert abnegation.pickername == f'{abnegation.title} (@{abnegation.name})'

        # scenario 2: when both name and title are given
        name = 'cullens'
        title = 'The Cullens'
        olympic_coven = models.Organization(title=title, owner=self.fixtures.crusoe)
        olympic_coven.name = name
        self.db_session.add(olympic_coven)
        self.db_session.commit()
        assert isinstance(olympic_coven.pickername, str)
        assert f'{title} (@{name})' in olympic_coven.pickername

    def test_organization_name(self):
        """Test for retrieving and setting an Organization's name."""
        insurgent = models.Organization(title="Insurgent", owner=self.fixtures.crusoe)
        with pytest.raises(ValueError):
            insurgent.name = '35453496*%&^$%^'
        with pytest.raises(ValueError):
            insurgent.name = '-Insurgent'
        insurgent.name = 'insurgent'
        assert insurgent.name == 'insurgent'
        insurgent.name = 'Insurgent'
        assert insurgent.name == 'Insurgent'
