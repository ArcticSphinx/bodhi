# -*- coding: utf-8 -*-
"""Test suite for the Bodhi models"""

import time

from nose.tools import eq_, raises
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from bodhi import models as model
from bodhi.models import (UpdateStatus, UpdateType, UpdateRequest,
                          UpdateSeverity, UpdateSuggestion)
from bodhi.tests.models import ModelTest
from bodhi.exceptions import InvalidRequest
from bodhi.config import config


class TestRelease(ModelTest):
    """Unit test case for the ``Release`` model."""
    klass = model.Release
    attrs = dict(
        name=u"F11",
        long_name=u"Fedora 11",
        id_prefix=u"FEDORA",
        dist_tag=u"dist-f11",
        version=11,
        locked=False,
        metrics={'test_metric': [0, 1, 2, 3, 4]}
        )

    def test_tags(self):
        eq_(self.obj.stable_tag, 'dist-f11-updates')
        eq_(self.obj.testing_tag, 'dist-f11-updates-testing')
        eq_(self.obj.candidate_tag, 'dist-f11-updates-candidate')


class TestEPELRelease(ModelTest):
    """Unit test case for the ``Release`` model."""
    klass = model.Release
    attrs = dict(
        name=u"EL5",
        long_name=u"Fedora EPEL 5",
        id_prefix=u"FEDORA-EPEL",
        dist_tag=u"dist-5E-epel",
        _candidate_tag=u"dist-5E-epel-testing-candidate",
        _testing_tag=u"dist-5E-epel-testing",
        _stable_tag=u"dist-5E-epel",
        version=5,
        )

    def test_tags(self):
        eq_(self.obj.stable_tag, 'dist-5E-epel')
        eq_(self.obj.testing_tag, 'dist-5E-epel-testing')
        eq_(self.obj.candidate_tag, 'dist-5E-epel-testing-candidate')


class TestPackage(ModelTest):
    """Unit test case for the ``Package`` model."""
    klass = model.Package
    attrs = dict(name=u"TurboGears")

    def do_get_dependencies(self):
        return dict(
            committers=[model.User(name=u'lmacken')]
        )

    def test_wiki_test_cases(self):
        """Test querying the wiki for test cases"""
        config['query_wiki_test_cases'] = True
        pkg = model.Package(name=u'gnome-shell')
        pkg.fetch_test_cases(model.DBSession())
        assert pkg.test_cases

    def test_committers(self):
        assert self.obj.committers[0].name == u'lmacken'


class TestBuild(ModelTest):
    """Unit test case for the ``Build`` model."""
    klass = model.Build
    attrs = dict(
        nvr=u"TurboGears-1.0.8-3.fc11",
        inherited=False,
        )

    def do_get_dependencies(self):
        return dict(
                release=model.Release(**TestRelease.attrs),
                package=model.Package(**TestPackage.attrs),
                )

    def test_release_relation(self):
        eq_(self.obj.release.name, u"F11")
        eq_(len(self.obj.release.builds), 1)
        eq_(self.obj.release.builds[0], self.obj)

    def test_package_relation(self):
        eq_(self.obj.package.name, u"TurboGears")
        eq_(len(self.obj.package.builds), 1)
        eq_(self.obj.package.builds[0], self.obj)

    #def test_latest(self):
    #    # Note, this build is hardcoded in bodhi/buildsys.py:DevBuildsys
    #    eq_(self.obj.get_latest(), u"TurboGears-1.0.8-7.fc11")

    #def test_latest_with_eq_build(self):
    #    self.obj.nvr = 'TurboGears-1.0.8-7.fc11'
    #    eq_(self.obj.get_latest(), None)

    #def test_latest_with_newer_build(self):
    #    self.obj.nvr = 'TurboGears-1.0.8-8.fc11'
    #    eq_(self.obj.get_latest(), None)

    #def test_latest_srpm(self):
    #    eq_(self.obj.get_latest_srpm(), os.path.join(config.get('build_dir'),
    #        'TurboGears/1.0.8/7.fc11/src/TurboGears-1.0.8-7.fc11.src.rpm'))

    def test_url(self):
        eq_(self.obj.get_url(), '/TurboGears-1.0.8-3.fc11')


class TestUpdate(ModelTest):
    """Unit test case for the ``Update`` model."""
    klass = model.Update
    attrs = dict(
        title=u'TurboGears-1.0.8-3.fc11',
        type=UpdateType.security,
        status=UpdateStatus.pending,
        request=UpdateRequest.testing,
        severity=UpdateSeverity.medium,
        suggest=UpdateSuggestion.reboot,
        stable_karma=3,
        unstable_karma=-3,
        close_bugs=True,
        notes=u'foobar',
        karma=0,
        )

    def do_get_dependencies(self):
        release = model.Release(**TestRelease.attrs)
        return dict(
            builds=[model.Build(nvr=u'TurboGears-1.0.8-3.fc11',
                                  package=model.Package(**TestPackage.attrs),
                                  release=release)],
            bugs=[model.Bug(bug_id=1), model.Bug(bug_id=2)],
            cves=[model.CVE(cve_id=u'CVE-2009-0001')],
            release=release,
            user=model.User(name=u'lmacken')
            )

    def get_update(self, name=u'TurboGears-1.0.8-3.fc11'):
        attrs = self.attrs.copy()
        pkg = model.DBSession.query(model.Package) \
                .filter_by(name=u'TurboGears').one()
        rel = model.DBSession.query(model.Release) \
                .filter_by(name=u'F11').one()
        attrs.update(dict(
            builds=[model.Build(nvr=name, package=pkg, release=rel)],
            release=rel,
            ))
        return self.klass(**attrs)

    def test_builds(self):
        eq_(len(self.obj.builds), 1)
        eq_(self.obj.builds[0].nvr, u'TurboGears-1.0.8-3.fc11')
        eq_(self.obj.builds[0].release.name, u'F11')
        eq_(self.obj.builds[0].package.name, u'TurboGears')

    def test_title(self):
        eq_(self.obj.title, u'TurboGears-1.0.8-3.fc11')

    def test_pkg_str(self):
        """ Ensure str(pkg) is correct """
        eq_(str(self.obj.builds[0].package), '================================================================================\n     TurboGears\n================================================================================\n\n Pending Updates (1)\n    o TurboGears-1.0.8-3.fc11\n')

    def test_bugstring(self):
        eq_(self.obj.get_bugstring(), u'1 2')

    def test_cvestring(self):
        eq_(self.obj.get_cvestring(), u'CVE-2009-0001')

    def test_assign_alias(self):
        update = self.obj
        update.assign_alias()
        year = time.localtime()[0]
        eq_(update.alias, u'%s-%s-0001' % (update.release.id_prefix, year))
        #assert update.date_pushed

        update = self.get_update(name=u'TurboGears-0.4.4-8.fc11')
        update.assign_alias()
        eq_(update.alias, u'%s-%s-0002' % (update.release.id_prefix, year))

        ## Create another update for another release that has the same
        ## Release.id_prefix.  This used to trigger a bug that would cause
        ## duplicate IDs across Fedora 10/11 updates.
        update = self.get_update(name=u'nethack-3.4.5-1.fc10')
        otherrel = model.Release(name=u'fc10', long_name=u'Fedora 10',
                                 id_prefix=u'FEDORA', dist_tag=u'dist-fc10')
        update.release = otherrel
        update.assign_alias()
        eq_(update.alias, u'%s-%s-0003' % (update.release.id_prefix, year))

        ## 10k bug
        update.alias = u'FEDORA-%s-9999' % year
        newupdate = self.get_update(name=u'nethack-2.5.6-1.fc10')
        newupdate.release = otherrel
        newupdate.assign_alias()
        eq_(newupdate.alias, u'FEDORA-%s-10000' % year)

        newerupdate = self.get_update(name=u'nethack-2.5.7-1.fc10')
        newerupdate.assign_alias()
        eq_(newerupdate.alias, u'FEDORA-%s-10001' % year)

        ## test updates that were pushed at the same time.  assign_alias should
        ## be able to figure out which one has the highest id.
        now = datetime.utcnow()
        newupdate.date_pushed = now
        newerupdate.date_pushed = now

        newest = self.get_update(name=u'nethack-2.5.8-1.fc10')
        newest.assign_alias()
        eq_(newest.alias, u'FEDORA-%s-10002' % year)

    def test_epel_id(self):
        """ Make sure we can handle id_prefixes that contain dashes.
        eg: FEDORA-EPEL
        """
        # Create a normal Fedora update first
        update = self.obj
        update.assign_alias()
        eq_(update.alias, u'FEDORA-%s-0001' % time.localtime()[0])

        update = self.get_update(name=u'TurboGears-2.1-1.el5')
        release = model.Release(name=u'EL-5', long_name=u'Fedora EPEL 5',
                          dist_tag=u'dist-5E-epel', id_prefix=u'FEDORA-EPEL')
        update.release = release
        update.assign_alias()
        eq_(update.alias, u'FEDORA-EPEL-%s-0001' % time.localtime()[0])

        update = self.get_update(name=u'TurboGears-2.2-1.el5')
        update.release = release
        update.assign_alias()
        eq_(update.alias, u'%s-%s-0002' % (release.id_prefix,
                                          time.localtime()[0]))

    @raises(IntegrityError)
    def test_dupe(self):
        self.get_update()
        self.get_update()

    def test_stable_karma(self):
        update = self.obj
        update.request = None
        eq_(update.karma, 0)
        eq_(update.request, None)
        update.comment(u"foo", 1, u'foo')
        eq_(update.karma, 1)
        eq_(update.request, None)
        update.comment(u"foo", 1, u'bar')
        eq_(update.karma, 2)
        eq_(update.request, None)
        update.comment(u"foo", 1, u'biz')
        eq_(update.karma, 3)
        eq_(update.request, UpdateRequest.stable)

    def test_unstable_karma(self):
        update = self.obj
        update.status = UpdateStatus.testing
        eq_(update.karma, 0)
        eq_(update.status, UpdateStatus.testing)
        update.comment(u"foo", -1, u'foo')
        eq_(update.status, UpdateStatus.testing)
        eq_(update.karma, -1)
        update.comment(u"bar", -1, u'bar')
        eq_(update.status, UpdateStatus.testing)
        eq_(update.karma, -2)
        update.comment(u"biz", -1, u'biz')
        eq_(update.karma, -3)
        eq_(update.status, UpdateStatus.obsolete)

    def test_update_bugs(self):
        update = self.obj
        eq_(len(update.bugs), 2)

        # try just adding bugs
        bugs = ['1234']
        update.update_bugs(bugs)
        eq_(len(update.bugs), 1)
        eq_(update.bugs[0].bug_id, 1234)

        # try just removing
        bugs = []
        update.update_bugs(bugs)
        eq_(len(update.bugs), 0)
        eq_(model.DBSession.query(model.Bug)
                .filter_by(bug_id=1234).first(), None)

        # Test new duplicate bugs
        bugs = ['1234', '1234']
        update.update_bugs(bugs)
        assert len(update.bugs) == 1

        # Try adding a new bug, and removing the rest
        bugs = ['4321']
        update.update_bugs(bugs)
        assert len(update.bugs) == 1
        assert update.bugs[0].bug_id == 4321
        eq_(model.DBSession.query(model.Bug)
                .filter_by(bug_id=1234).first(), None)

    def test_set_request_unpush(self):
        eq_(self.obj.status, UpdateStatus.pending)
        self.obj.status = UpdateStatus.testing
        self.obj.set_request('unpush')
        eq_(self.obj.status, UpdateStatus.unpushed)

    @raises(InvalidRequest)
    def test_set_request_testing(self):
        self.obj.set_request('testing')

    def test_set_request_stable(self):
        eq_(self.obj.status, UpdateStatus.pending)
        self.obj.set_request('stable')
        eq_(self.obj.status, UpdateStatus.pending)
        # TODO: verify results (via session flash?)

    def test_set_request_obsolete(self):
        eq_(self.obj.status, UpdateStatus.pending)
        self.obj.set_request('obsolete')
        eq_(self.obj.status, UpdateStatus.obsolete)

    def test_request_complete(self):
        self.obj.request = None
        eq_(self.obj.date_pushed, None)
        self.obj.set_request('testing')
        self.obj.request_complete()
        assert self.obj.date_pushed
        eq_(self.obj.status, UpdateStatus.testing)

    def test_status_comment(self):
        self.obj.status = UpdateStatus.testing
        self.obj.status_comment()
        eq_(len(self.obj.comments), 1)
        eq_(self.obj.comments[0].user.name, u'bodhi')
        eq_(self.obj.comments[0].text,
                u'This update has been pushed to testing')
        self.obj.status = UpdateStatus.stable
        self.obj.status_comment()
        eq_(len(self.obj.comments), 2)
        eq_(self.obj.comments[1].user.name, u'bodhi')
        eq_(self.obj.comments[1].text,
                u'This update has been pushed to stable')

    def test_get_url(self):
        eq_(self.obj.get_url(), u'/TurboGears-1.0.8-3.fc11')
        self.obj.assign_alias()
        eq_(self.obj.get_url(), u'/F11/FEDORA-%s-0001' % time.localtime()[0])

    def test_get_build_tag(self):
        eq_(self.obj.get_build_tag(), u'dist-f11-updates-candidate')
        self.obj.status = UpdateStatus.testing
        eq_(self.obj.get_build_tag(), u'dist-f11-updates-testing')
        self.obj.status = UpdateStatus.stable
        eq_(self.obj.get_build_tag(), u'dist-f11-updates')


class TestUser(ModelTest):
    klass = model.User
    attrs = dict(name=u'Bob Vila')

    def do_get_dependencies(self):
        group = model.Group(name=u'proventesters')
        return dict(groups=[group])


class TestGroup(ModelTest):
    klass = model.Group
    attrs = dict(name=u'proventesters')

    def do_get_dependencies(self):
        user = model.User(name=u'bob')
        return dict(users=[user])

