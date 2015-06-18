.. _algo:

*************************
Composants algorithmiques
*************************

Liste des composants
--------------------

Comment toujours, interrogeons le collectuer dédié aux composants algorithmiques::

    >>> pprint.pprint(fpx.components())
    [<class 'common.algo.coupling.Coupling'>,
     <class 'vortex.algo.components.Expresso'>,
     <class 'common.algo.stdpost.Fa2Grib'>,
     <class 'common.algo.assim.PseudoTrajectory'>,
     <class 'vortex.algo.components.BlindRun'>,
     <class 'common.algo.forecasts.DFIForecast'>,
     <class 'common.algo.assim.Minim'>,
     <class 'common.algo.odbtools.OdbMatchup'>,
     <class 'common.algo.stdpost.AddField'>,
     <class 'common.algo.odbtools.OdbAverage'>,
     <class 'common.algo.odbtools.Raw2ODB'>,
     <class 'common.algo.forecasts.FullPos'>,
     <class 'common.algo.assim.Screening'>,
     <class 'common.algo.assim.MergeVarBC'>,
     <class 'common.algo.forecasts.LAMForecast'>,
     <class 'common.algo.assim.Canari'>,
     <class 'vortex.algo.components.Parallel'>,
     <class 'common.algo.forecasts.Forecast'>]
