#!/usr/bin/python -tt

"""
Verify that all builds that are tagged as updates in koji have the
correct status within bodhi
"""

from turbogears.database import PackageHub
from bodhi.tools.init import load_config
from bodhi.model import PackageBuild
from bodhi.buildsys import get_session
from sqlobject import SQLObjectNotFound

load_config()
__connection__ = hub = PackageHub("bodhi")

koji = get_session()

for tag in ('dist-fc7-updates-testing', 'dist-fc7-updates',
            'dist-f8-updates-testing', 'dist-f8-updates'):
    tagged = [build['nvr'] for build in koji.listTagged(tag)]
    for nvr in tagged:
        try:
            build = PackageBuild.byNvr(nvr)
        except SQLObjectNotFound:
            print "%s not found!" % nvr
            continue
        if not build.update:
            print "%s has no update" % (build.nvr)
        status = 'testing' in tag and 'testing' or 'stable'
        if build.update.status != status:
            print "%s not %s" % (build.nvr, status)