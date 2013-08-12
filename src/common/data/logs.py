#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.flow import FlowResource


class Listing(FlowResource):

    _footprint = [
        dict(
             info = 'Listing',
             attr = dict(
                task = dict(),
                kind = dict(
                    values = [ 'listing' ]
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'listing'

    def basename_info(self):
        """Generic information, radical = ``listing``."""
        return dict(
            radical = 'listing',
            src     = [ self.model, self.task.split('/').pop() ],
        )
