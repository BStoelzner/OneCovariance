import time
import numpy as np
from scipy.signal import argrelextrema
from scipy.interpolate import UnivariateSpline

import levin

try:
    from onecov.cov_ell_space import CovELLSpace
except:
    from cov_ell_space import CovELLSpace


class CovCOSEBI(CovELLSpace):
    """
    This class calculates the covariance for COSEBI estimator of the
    shear-shear correlation. Inherits the functionality of the
    CovELLSpace class.

    Parameters
    ----------
    cov_dict : dictionary
        Specifies which terms of the covariance (Gaussian, non-Gaussian,
        super-sample covariance) should be calculated. To be passed from
        the read_input method of the Input class.
    obs_dict : dictionary
        with the following keys (To be passed from the read_input method
        of the Input class.)
        'observables' : dictionary
            Specifies which observables (cosmic shear, galaxy-galaxy
            lensing and/or clustering) should be calculated. Also,
            indicates whether cross-terms are evaluated.
        'ELLspace' : dictionary
            Specifies the exact details of the projection to ell space.
            The projection from wavefactor k to angular scale ell is
            done first, followed by the projection to real space in this
            class
        'THETAspace' : dictionary
            Specifies the exact details of the projection to real space,
            e.g., theta_min/max and the number of theta bins to be
            calculated.
        'COSEBIs' : dictionary
            Specifies the exact details of the projection to COSEBIs,
            e.g. the number of modes to be calculated.
        'bandpowers' : dictionary
            Specifies the exact details of the projection to bandpowers,
            e.g. the ell modes and their spacing.
    cosmo_dict : dictionary
        Specifies all cosmological parameters. To be passed from the
        read_input method of the Input class.
    bias_dict : dictionary
        Specifies all the information about the bias model. To be passed
        from the read_input method of the Input class.
    hod_dict : dictionary
        Specifies all the information about the halo occupation
        distribution used. This defines the shot noise level of the
        covariance and includes the mass bin definition of the different
        galaxy populations. To be passed from the read_input method of
        the Input class.
    survey_params_dict : dictionary
        Specifies all the information unique to a specific survey.
        Relevant values are the effective number density of galaxies for
        all tomographic bins as well as the ellipticity dispersion for
        galaxy shapes. To be passed from the read_input method of the
        Input class.
    prec : dictionary
        with the following keys (To be passed from the read_input method
        of the Input class.)
        'hm' : dictionary
            Contains precision information about the HaloModel (also,
            see hmf documentation by Steven Murray), this includes mass
            range and spacing for the mass integrations in the halo
            model.
        'powspec' : dictionary
            Contains precision information about the power spectra, this
            includes k-range and spacing.
        'trispec' : dictionary
            Contains precision information about the trispectra, this
            includes k-range and spacing and the desired precision
            limits.
    read_in_tables : dictionary
        with the following keys (To be passed from the read_input method
        of the FileInput class.)
        'zclust' : dictionary
            Look-up table for the clustering redshifts and their number
            of tomographic bins. Relevant for clustering and galaxy-
            galaxy lensing estimators.
        'zlens' : dictionary
            Look-up table for the lensing redshifts and their number of
            tomographic bins. Relevant for cosmic shear and galaxy-
            galaxy lensing estimators.
        'survey_area_clust' : dictionary
            Contains information about the survey footprint that is read
            from the fits file of the survey (processed by healpy).
            Possible keys: 'area', 'ell', 'a_lm'
        'Pxy' : dictionary
            default : None
            Look-up table for the power spectra (matter-matter, tracer-
            tracer, matter-tracer, optional).
        'Cxy' : dictionary
            default : None
            Look-up table for the C_ell projected power spectra (matter-
            matter, tracer- tracer, matter-tracer, optional).
        'effbias' : dictionary
            default : None
            Look-up table for the effective bias as a function of
            redshift(optional).
        'mor' : dictionary
            default : None
            Look-up table for the mass-observable relation (optional).
        'occprob' : dictionary
            default : None
            Look-up table for the occupation probability as a function
            of halo mass per galaxy sample (optional).
        'occnum' : dictionary
            default : None
            Look-up table for the occupation number as a function of
            halo mass per galaxy sample (optional).
        'tri' : dictionary
            Look-up table for the trispectra (for all combinations of
            matter 'm' and tracer 'g', optional).
            Possible keys: '', 'z', 'mmmm', 'mmgm', 'gmgm', 'ggmm',
            'gggm', 'gggg'
        'cosebis' : dictionary
            Look-up tables for calculating COSEBIs. Currently the code
            cannot generate the roots and normalizations for the kernel
            functions itself, so either the kernel's roots and
            normalizations or the kernel (W_n) itself must be given.
            Possible keys: 'wn_log_ell', 'wn_log', 'wn_lin_ell',
                           'wn_lin', 'norms', 'roots'

    Attributes
    ----------
    see CovELLSpace class

    Example :
    ---------
    from cov_input import Input, FileInput
    from cov_cosebis import CovCOSEBI
    inp = Input()
    covterms, observables, output, cosmo, bias, hod, survey_params, \
        prec = inp.read_input()
    fileinp = FileInput()
    read_in_tables = fileinp.read_input(inp.config_name)
    covcosebi = CovCOSEBI(covterms, observables, output, cosmo, bias,
        hod, survey_params, prec, read_in_tables)

    """

    def __init__(self,
                 cov_dict,
                 obs_dict,
                 output_dict,
                 cosmo_dict,
                 bias_dict,
                 iA,
                 hod_dict,
                 survey_params_dict,
                 prec,
                 read_in_tables):
        self.En_modes = obs_dict['COSEBIs']['En_modes']
        self.array_En_modes = np.array([i +1 for i in range(self.En_modes)]).astype(int)
        self.wn_ells, self.wn_kernels = \
            self.__get_wn_kernels(read_in_tables['COSEBIs'])
        self.ell_limits = []
        for mode in range(self.En_modes):
            limits_at_mode = np.array(self.wn_ells[argrelextrema(self.wn_kernels[mode], np.less)[0][:]])[::20]
            limits_at_mode_append = np.zeros(len(limits_at_mode) + 2)
            limits_at_mode_append[1:-1] = limits_at_mode
            limits_at_mode_append[0] = self.wn_ells[0]
            limits_at_mode_append[-1] = self.wn_ells[-1]
            self.ell_limits.append(limits_at_mode_append)
        
        self.levin_int = levin.Levin(0, 16, 32, obs_dict['COSEBIs']['En_acc']/np.sqrt(len(self.ell_limits[0][:])), self.integration_intervals)
        self.levin_int.init_w_ell(self.wn_ells, np.array(self.wn_kernels).T)
        
        self.__get_Tn_pm(read_in_tables['COSEBIs'], obs_dict['COSEBIs']) 
        obs_dict['ELLspace']['ell_min'] = self.wn_ells[0]
        obs_dict['ELLspace']['ell_max'] = self.wn_ells[-1]
        obs_dict['ELLspace']['ell_bins'] = 100
        obs_dict['ELLspace']['ell_type'] = 'log'
        CovELLSpace.__init__(self,
                             cov_dict,
                             obs_dict,
                             output_dict,
                             cosmo_dict,
                             bias_dict,
                             iA,
                             hod_dict,
                             survey_params_dict,
                             prec,
                             read_in_tables)
        self.theta_integral = np.geomspace(obs_dict['COSEBIs']['theta_min'], obs_dict['COSEBIs']['theta_max'], 1000) 
        self.dnpair_gg, self.dnpair_gm, self.dnpair_mm, self.theta_gg, self.theta_gm, self.theta_mm  = self.get_dnpair([self.gg, self.gm, self.mm],
                                                                                                                        self.theta_integral,
                                                                                                                        survey_params_dict,
                                                                                                                        read_in_tables['npair'])
        
        if self.cov_dict['gauss']:
            self.E_mode_gg, self.E_mode_gm, self.E_mode_mm = self.calc_E_mode()


    def __get_wn_kernels(self,
                         cosebi_tabs):

        for wn_style in ['log', 'lin']:
            if cosebi_tabs['wn_'+wn_style] is not None:
                return cosebi_tabs['wn_'+wn_style+'_ell'], \
                    cosebi_tabs['wn_'+wn_style]

        raise Exception("ConfigError: To calculate the COSEBI " +
                        "covariance the W_n kernels must be provided as an " +
                        "external table. Must be included in [tabulated inputs " +
                        "files] as 'wn_log_file' or 'wn_lin_file' to go on.")

        # insert calc of Wn at some point
    
    def __get_Tn_pm(self,
                    cosebi_tabs,
                    covCOSEBIsettings):
        self.Tn_p = []
        self.Tn_m = []
        if cosebi_tabs['Tn_p'] is not None:
            for i_mode in range(len(cosebi_tabs['Tn_p'][:,0])):
                self.Tn_p.append(UnivariateSpline(cosebi_tabs['Tn_pm_theta'],  cosebi_tabs['Tn_p'][i_mode,:], k=2, s=0, ext=0))
                self.Tn_m.append(UnivariateSpline(cosebi_tabs['Tn_pm_theta'],  cosebi_tabs['Tn_m'][i_mode,:], k=2, s=0, ext=0))
            if cosebi_tabs['Tn_pm_theta'][0] > covCOSEBIsettings['theta_min'] or cosebi_tabs['Tn_pm_theta'][-1] < covCOSEBIsettings['theta_max']:
                print("Warning: To calculate the shot noise contribution for COSEBI "+
                    "I will have to extrapolate Tn_pm. "+
                    "Please check the angular support for Tn_pm file." + 
                    "Should be from " + str(covCOSEBIsettings['theta_min']) + " to " + 
                    str(covCOSEBIsettings['theta_max']) + ", but is only given in " +
                    str(cosebi_tabs['Tn_pm_theta'][0]) + " to " + str(cosebi_tabs['Tn_pm_theta'][-1]) + ".")
        else:
            raise Exception("ConfigError: To calculate the COSEBI " +
                        "covariance the Tn_pm kernels must be provided as an " +
                        "external table. Must be included in [tabulated inputs " +
                        "files] as 'Tn_plus_file' and 'Tn_minus_file' to go on.")

    def calc_E_mode(self):
        """
        Calculates the E-mode signal of the COSEBis in all tomographic bin
        combination and all tracers specified using the Gauss Legendre integrator.

        Parameters
        ----------
        covCOSEBIsettings : dictionary
            Specifies the exact details of the COSEBI calculation,
            e.g., theta_min/max and the number of modes to be
            calculated.

        Returns
        -------
        E_mode_mm : array
            An numpy array containing all E modes for cosmic shear with
            the following shape:
            (E_mode order, sample_bin, tomo_bin_i, tomo_bin_j)

        """

        E_mode_mm = np.zeros((self.En_modes, self.sample_dim,
                              self.n_tomo_lens, self.n_tomo_lens))
        E_mode_gm = np.zeros((self.En_modes, self.sample_dim,
                              self.n_tomo_clust, self.n_tomo_lens))
        E_mode_gg = np.zeros((self.En_modes, self.sample_dim,
                              self.n_tomo_clust, self.n_tomo_clust))
        
        if (self.mm or self.gm):
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes
            original_shape = self.Cell_mm[0, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**2
            Cell_mm_flat = np.reshape(self.Cell_mm, (len(
                self.ellrange), flat_length))
            for mode in range(self.En_modes):
                self.levin_int.init_integral(self.ellrange, Cell_mm_flat*self.ellrange[:,None], True, True)
                E_mode_mm[mode,:,:,:] = 1 / 2 / np.pi * np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[mode][:], mode)),original_shape)
                eta = (time.time()-t0)/60 * (tcombs/tcomb-1)
                print('\rCOSEBI E-mode calculation for lensing at '
                        + str(round(tcomb/tcombs*100, 1)) + '% in '
                        + str(round(((time.time()-t0)/60), 1)) +
                        'min  ETA '
                        'in ' + str(round(eta, 1)) + 'min', end="")
                tcomb += 1
            print(" ")

        if (self.gm or (self.gg and self.mm and self.cross_terms)):
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes
            original_shape = self.Cell_gm[0, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens*self.n_tomo_clust
            Cell_gm_flat = np.reshape(self.Cell_gm, (len(
                self.ellrange), flat_length))
            for mode in range(self.En_modes):
                self.levin_int.init_integral(self.ellrange, Cell_gm_flat*self.ellrange[:,None], True, True)
                E_mode_gm[mode,:,:,:] = 1 / 2 / np.pi * np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[mode][:], mode)),original_shape)
                eta = (time.time()-t0)/60 * (tcombs/tcomb-1)
                print('\rCOSEBI E-mode calculation for GGL at '
                        + str(round(tcomb/tcombs*100, 1)) + '% in '
                        + str(round(((time.time()-t0)/60), 1)) +
                        'min  ETA '
                        'in ' + str(round(eta, 1)) + 'min', end="")
                tcomb += 1
                
            print(" ")

        if (self.gg or self.gm):
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes
            original_shape = self.Cell_gg[0, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**2
            Cell_gg_flat = np.reshape(self.Cell_gg, (len(
                self.ellrange), flat_length))
            for mode in range(self.En_modes):
                self.levin_int.init_integral(self.ellrange, Cell_gg_flat*self.ellrange[:,None], True, True)
                E_mode_gg[mode,:,:,:] = 1 / 2 / np.pi * np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[mode][:], mode)),original_shape)
                eta = (time.time()-t0)/60 * (tcombs/tcomb-1)
                print('\rCOSEBI E-mode calculation for clustering at '
                        + str(round(tcomb/tcombs*100, 1)) + '% in '
                        + str(round(((time.time()-t0)/60), 1)) +
                        'min  ETA '
                        'in ' + str(round(eta, 1)) + 'min', end="")
                tcomb += 1
            print(" ")

        return E_mode_gg, E_mode_gm, E_mode_mm

    def calc_covCOSEBI(self,
                       obs_dict,
                       output_dict,
                       bias_dict,
                       hod_dict,
                       survey_params_dict,
                       prec,
                       read_in_tables):
        """
        Calculates the full covariance for the defined observables 
        for the COSEBIs as specified in the config file.

        Parameters
        ----------
        obs_dict : dictionary
            with the following keys (To be passed from the read_input method
            of the Input class.)
            'observables' : dictionary
                Specifies which observables (cosmic shear, galaxy-galaxy
                lensing and/or clustering) should be calculated. Also,
                indicates whether cross-terms are evaluated.
            'ELLspace' : dictionary
                Specifies the exact details of the projection to ell space.
                The projection from wavefactor k to angular scale ell is
                done first, followed by the projection to real space in this
                class
            'THETAspace' : dictionary
                Specifies the exact details of the projection to real space,
                e.g., theta_min/max and the number of theta bins to be
                calculated.
            'COSEBIs' : dictionary
                Specifies the exact details of the projection to COSEBIs,
                e.g. the number of modes to be calculated.
            'bandpowers' : dictionary
                Specifies the exact details of the projection to bandpowers,
                e.g. the ell modes and their spacing.
        output_dict : dictionary
            Specifies whether a file for the trispectra should be 
            written to save computational time in the future. Gives the
            full path and name for the output file. To be passed from 
            the read_input method of the Input class.
        bias_dict : dictionary
            Specifies all the information about the bias model. To be passed
            from the read_input method of the Input class.
        hod_dict : dictionary
            Specifies all the information about the halo occupation
            distribution used. This defines the shot noise level of the
            covariance and includes the mass bin definition of the different
            galaxy populations. To be passed from the read_input method of
            the Input class.
        survey_params_dict : dictionary
            Specifies all the information unique to a specific survey.
            Relevant values are the effective number density of galaxies for
            all tomographic bins as well as the ellipticity dispersion for
            galaxy shapes. To be passed from the read_input method of the
            Input class.
        prec : dictionary
            with the following keys (To be passed from the read_input method
            of the Input class.)
            'hm' : dictionary
                Contains precision information about the HaloModel (also,
                see hmf documentation by Steven Murray), this includes mass
                range and spacing for the mass integrations in the halo
                model.
            'powspec' : dictionary
                Contains precision information about the power spectra, this
                includes k-range and spacing.
            'trispec' : dictionary
                Contains precision information about the trispectra, this
                includes k-range and spacing and the desired precision
                limits.
        read_in_tables : dictionary
            with the following keys (To be passed from the read_input method
            of the FileInput class.)
            'zclust' : dictionary
                Look-up table for the clustering redshifts and their number
                of tomographic bins. Relevant for clustering and galaxy-
                galaxy lensing estimators.
            'zlens' : dictionary
                Look-up table for the lensing redshifts and their number of
                tomographic bins. Relevant for cosmic shear and galaxy-
                galaxy lensing estimators.
            'survey_area_clust' : dictionary
                Contains information about the survey footprint that is read
                from the fits file of the survey (processed by healpy).
                Possible keys: 'area', 'ell', 'a_lm'
            'Pxy' : dictionary
                default : None
                Look-up table for the power spectra (matter-matter, tracer-
                tracer, matter-tracer, optional).
            'Cxy' : dictionary
                default : None
                Look-up table for the C_ell projected power spectra (matter-
                matter, tracer- tracer, matter-tracer, optional).
            'effbias' : dictionary
                default : None
                Look-up table for the effective bias as a function of
                redshift(optional).
            'mor' : dictionary
                default : None
                Look-up table for the mass-observable relation (optional).
            'occprob' : dictionary
                default : None
                Look-up table for the occupation probability as a function
                of halo mass per galaxy sample (optional).
            'occnum' : dictionary
                default : None
                Look-up table for the occupation number as a function of
                halo mass per galaxy sample (optional).
            'tri' : dictionary
                Look-up table for the trispectra (for all combinations of
                matter 'm' and tracer 'g', optional).
                Possible keys: '', 'z', 'mmmm', 'mmgm', 'gmgm', 'ggmm',
                'gggm', 'gggg'
            'cosebis' : dictionary
                Look-up tables for calculating COSEBIs. Currently the code
                cannot generate the roots and normalizations for the kernel
                functions itself, so either the kernel's roots and
                normalizations or the kernel (W_n) itself must be given.
                Possible keys: 'wn_log_ell', 'wn_log', 'wn_lin_ell',
                                'wn_lin', 'norms', 'roots'

        Returns
        -------
        gauss, nongauss, ssc : list of arrays
            each with 6 entries for the observables 
                ['gggg', 'gggm', 'ggmm', 'gmgm', 'mmgm', 'mmmm']
            each entry with shape (m_modes, n_modes, 
                                   sample bins, sample bins,
                                   no_tomo_clust\lens, no_tomo_clust\lens,
                                   no_tomo_clust\lens, no_tomo_clust\lens)
        """
        print("Calculating covariance for COSEBIs E_n")
        if not self.cov_dict['split_gauss']:
            gaussgggg, gaussgggm, gaussggmm, \
                gaussgmgm, gaussmmgm, gaussmmmm, \
                gaussgggg_sn, gaussgmgm_sn, gaussmmmm_sn = \
                self.covCOSEBI_gaussian(obs_dict,
                                        survey_params_dict)
            gauss = [gaussgggg + gaussgggg_sn, gaussgggm,
                     gaussggmm, gaussgmgm + gaussgmgm_sn,
                     gaussmmgm, gaussmmmm + gaussmmmm_sn]
        else:
            gauss = self.covCOSEBI_gaussian(obs_dict,
                                            survey_params_dict)

        nongauss = self.covCOSEBI_non_gaussian(obs_dict,
                                               survey_params_dict,
                                               output_dict,
                                               bias_dict,
                                               hod_dict,
                                               prec,
                                               read_in_tables['tri'])
        ssc = self.covCOSEBI_ssc(obs_dict,
                                 survey_params_dict,
                                 output_dict,
                                 bias_dict,
                                 hod_dict,
                                 prec,
                                 read_in_tables['tri'])

        return list(gauss), list(nongauss), list(ssc)

    def covCOSEBI_gaussian(self,
                           obs_dict,
                           survey_params_dict):
        """
        Calculates the Gaussian (disconnected) covariance for COSEBIs.


        Parameters
        ----------
        covELLspacesettings : dictionary
            ...
        survey_params_dict : dictionary
            Specifies all the information unique to a specific survey.
            Relevant values are the effective number density of galaxies
            for all tomographic bins as well as the ellipticity
            dispersion for galaxy shapes. To be passed from the
            read_input method of the Input class.
        calc_prefac : bool
            default : True
            If True, returns the full Cell-covariance. If False, it 
            omits the prefactor 1/(2*ell+1)/f_sky, where f_sky is the
            observed fraction on the sky.

        Returns
        -------
        gaussELLgggg, gaussELLgggm, gaussELLggmm, \
        gaussELLgmgm, gaussELLmmgm, gaussELLmmmm, \
        gaussELLgggg_sn, gaussELLgmgm_sn, gaussELLmmmm_sn : list of 
                                                            arrays
            with shape (ell bins, ell bins, 
                        sample bins, sample bins,
                        n_tomo_clust/lens, n_tomo_clust/lens, 
                        n_tomo_clust/lens, n_tomo_clust/lens)

        Note :
        ------
        The shot-noise terms are denoted with '_sn'. To get the full
        covariance contribution to the pure kappa-kappa ('mmmm'),
        tracer-tracer ('gggg'), and kappa-tracer ('gmgm') terms, one 
        needs to add gaussELLxxyy + gaussELLxxyy_sn. They are kept 
        separate for a later numerical integration.

        """

        if not self.cov_dict['gauss']:
            return 0, 0, 0, 0, 0, 0, 0, 0, 0

        print("Calculating gaussian covariance for COSEBIS")

        gaussCOSEBIgggg_sva, gaussCOSEBIgggg_mix, gaussCOSEBIgggg_sn, \
            gaussCOSEBIgggm_sva, gaussCOSEBIgggm_mix, gaussCOSEBIgggm_sn, \
            gaussCOSEBIggmm_sva, gaussCOSEBIggmm_mix, gaussCOSEBIggmm_sn, \
            gaussCOSEBIgmgm_sva, gaussCOSEBIgmgm_mix, gaussCOSEBIgmgm_sn, \
            gaussCOSEBImmgm_sva, gaussCOSEBImmgm_mix, gaussCOSEBImmgm_sn, \
            gaussCOSEBImmmm_sva, gaussCOSEBImmmm_mix, gaussCOSEBImmmm_sn = \
            self.__covCOSEBI_split_gaussian(obs_dict,
                                            survey_params_dict)
        if not self.cov_dict['split_gauss']:
            gaussCOSEBIgggg = gaussCOSEBIgggg_sva + gaussCOSEBIgggg_mix
            gaussCOSEBIgggm = gaussCOSEBIgggm_sva + gaussCOSEBIgggm_mix
            gaussCOSEBIgmgm = gaussCOSEBIgmgm_sva + gaussCOSEBIgmgm_mix
            gaussCOSEBImmgm = gaussCOSEBImmgm_sva + gaussCOSEBImmgm_mix
            gaussCOSEBImmmm = gaussCOSEBImmmm_sva + gaussCOSEBImmmm_mix
            gaussCOSEBIggmm = gaussCOSEBIggmm_sva + gaussCOSEBIggmm_mix
            return gaussCOSEBIgggg, gaussCOSEBIgggm, gaussCOSEBIggmm, \
                gaussCOSEBIgmgm, gaussCOSEBImmgm, gaussCOSEBImmmm, \
                gaussCOSEBIgggg_sn, gaussCOSEBIgmgm_sn, gaussCOSEBImmmm_sn
        else:
            return gaussCOSEBIgggg_sva, gaussCOSEBIgggg_mix, gaussCOSEBIgggg_sn, \
                gaussCOSEBIgggm_sva, gaussCOSEBIgggm_mix, gaussCOSEBIgggm_sn, \
                gaussCOSEBIggmm_sva, gaussCOSEBIggmm_mix, gaussCOSEBIggmm_sn, \
                gaussCOSEBIgmgm_sva, gaussCOSEBIgmgm_mix, gaussCOSEBIgmgm_sn, \
                gaussCOSEBImmgm_sva, gaussCOSEBImmgm_mix, gaussCOSEBImmgm_sn, \
                gaussCOSEBImmmm_sva, gaussCOSEBImmmm_mix, gaussCOSEBImmmm_sn

    def __covCOSEBI_split_gaussian(self,
                                   obs_dict,
                                   survey_params_dict):
        """
        Calculates the Gaussian (disconnected) covariance for COSEBIs
        between two observables.

        Parameters
        ----------
        ccovCOSEBIsettings : dictionary
            Specifies the exact details of the COSEBI calculation,
            e.g., theta_min/max and the number of modes to be
            calculated.
        survey_params_dict : dictionary
            Specifies all the information unique to a specific survey.
            Relevant values are the effective number density of galaxies
            for all tomographic bins as well as the ellipticity
            dispersion for galaxy shapes. To be passed from the
            read_input method of the Input class.

        Returns
        -------
        gaussCOSEBIgggg, gaussCOSBEIgggm, gaussCOSEBIggmm, \
        gaussCOSEBIgmgm, gaussCOSEBImmgm, gaussCOSEBImmmm, \
        gaussCOSEBIgggg_sn, gaussCOSEBIgmgm_sn, gaussCOSEBImmmm_sn : list of
                                                            arrays
            with shape (number of modes, number of modes,
                        sample bins, sample bins,
                        n_tomo_clust/lens, n_tomo_clust/lens,
                        n_tomo_clust/lens, n_tomo_clust/lens)

        Note :
        ------
        The shot-noise terms are denoted with '_sn'. To get the full
        covariance contribution to the pure kappa-kappa ('mmmm'),
        tracer-tracer ('gggg'), and kappa-tracer ('gmgm') terms, one
        needs to add gaussCOSEBIxxyy + gaussCOSEBIxxyy_sn. They are kept
        separate for a later numerical integration.

        """

        if not self.cov_dict['gauss']:
            return 0, 0, 0, 0, 0, 0, 0, 0, 0
        save_entry = self.cov_dict['split_gauss']
        self.cov_dict['split_gauss'] = True
        gaussELLgggg_sva, gaussELLgggg_mix, _, \
            gaussELLgggm_sva, gaussELLgggm_mix, _, \
            gaussELLggmm_sva, _, _, \
            gaussELLgmgm_sva, gaussELLgmgm_mix, _, \
            gaussELLmmgm_sva, gaussELLmmgm_mix, _, \
            gaussELLmmmm_sva, gaussELLmmmm_mix, _ = self.covELL_gaussian(
                obs_dict['ELLspace'], survey_params_dict, False)
        self.cov_dict['split_gauss'] = save_entry
        gaussCOSEBIgggg_sva = None
        gaussCOSEBIgggg_mix = None
        gaussCOSEBIgggg_sn = None

        gaussCOSEBIgggm_sva = None
        gaussCOSEBIgggm_mix = None
        gaussCOSEBIgggm_sn = None

        gaussCOSEBIggmm_sva = None
        gaussCOSEBIggmm_mix = None
        gaussCOSEBIggmm_sn = None

        gaussCOSEBIgmgm_sva = None
        gaussCOSEBIgmgm_mix = None
        gaussCOSEBIgmgm_sn = None

        gaussCOSEBImmgm_sva = None
        gaussCOSEBImmgm_mix = None
        gaussCOSEBImmgm_sn = None

        gaussCOSEBImmmm_sva = None
        gaussCOSEBImmmm_mix = None
        gaussCOSEBImmmm_sn = None

        if self.gg or self.gm:
            kron_delta_tomo_clust = np.diag(np.ones(self.n_tomo_clust))
        if self.mm or self.gm:
            kron_delta_tomo_lens = np.diag(np.ones(self.n_tomo_lens))

        if self.gg:
            gaussCOSEBIgggg_sva = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust))
            gaussCOSEBIgggg_mix = np.zeros_like(gaussCOSEBIgggg_sva)
            gaussCOSEBIgggg_sn = np.zeros_like(gaussCOSEBIgggg_sva)
            original_shape = gaussCOSEBIgggg_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**4
            gaussELL_sva_flat = np.reshape(gaussELLgggg_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLgggg_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gaussCOSEBIgggg_sva[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBIgggg_sva[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBIgggg_sva[m_mode, n_mode, :, :, :, :, :, :]
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gaussCOSEBIgggg_mix[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBIgggg_mix[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBIgggg_mix[m_mode, n_mode, :, :, :, :, :, :]
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    Tpm_product = self.Tn_p[m_mode](self.theta_gg)*self.Tn_p[n_mode](self.theta_gg) + self.Tn_m[m_mode](self.theta_gg)*self.Tn_m[n_mode](self.theta_gg)
                    integrand = (Tpm_product*self.theta_gg**2)[:,None, None]/self.dnpair_gg
                    aux_gg_sn = np.trapz(integrand,self.theta_gg,axis=0)/self.arcmin2torad2**2
                    gaussCOSEBIgggg_sn[n_mode, m_mode, :, :, :, :, :, :] = (kron_delta_tomo_clust[None, None, :, None, :, None]
                                                                            * kron_delta_tomo_clust[None, None, None, :, None, :]
                                                                            + kron_delta_tomo_clust[None, None, :, None, None, :]
                                                                            * kron_delta_tomo_clust[None, None, None, :, :, None]) \
                                                                            * (np.ones(self.n_tomo_clust)[None, :]**2*np.ones(self.n_tomo_clust)[:, None]**2*aux_gg_sn)[None, None, :, :, None, None]/4.
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'gggg term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1

            print(" ")
        else:
            gaussCOSEBIgggg_sva = 0
            gaussCOSEBIgggg_mix = 0
            gaussCOSEBIgggg_sn = 0

        if self.gg and self.gm and self.cross_terms:
            gaussCOSEBIgggm_sn = 0
            gaussCOSEBIgggm_sva = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_lens))
            gaussCOSEBIgggm_mix = np.zeros_like(gaussCOSEBIgggm_sva)
            original_shape = gaussCOSEBIgggm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens*self.n_tomo_clust**3
            gaussELL_sva_flat = np.reshape(gaussELLgggm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLgggm_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    survey_area = max(survey_params_dict['survey_area_clust'],survey_params_dict['survey_area_ggl'])   
                    gaussCOSEBIgggm_sva[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_area/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBIgggm_sva[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBIgggm_sva[m_mode, n_mode, :, :, :, :, :, :]
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gaussCOSEBIgggm_mix[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_area/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBIgggm_mix[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBIgggm_mix[m_mode, n_mode, :, :, :, :, :, :]
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'gggm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print(" ")
        else:
            gaussCOSEBIgggm_sva = 0
            gaussCOSEBIgggm_mix = 0
            gaussCOSEBIgggm_sn = 0

        if self.gg and self.mm and self.cross_terms:
            gaussCOSEBIggmm_sva = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_lens, self.n_tomo_lens))
            gaussCOSEBIggmm_mix = 0
            gaussCOSEBIggmm_sn = 0
            original_shape = gaussCOSEBIggmm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**2*self.n_tomo_clust**2
            gaussELL_sva_flat = np.reshape(gaussELLggmm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    survey_area = max(survey_params_dict['survey_area_clust'],survey_params_dict['survey_area_lens'])
                    gaussCOSEBIggmm_sva[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_area/self.deg2torad2) *  np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBIggmm_sva[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBIggmm_sva[m_mode, n_mode, :, :, :, :, :, :]
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'ggmm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print(" ")
        else:
            gaussCOSEBIggmm_sva = 0
            gaussCOSEBIggmm_mix = 0
            gaussCOSEBIggmm_sn = 0

        if self.gm:
            gaussCOSEBIgmgm_sva = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_lens, self.n_tomo_clust, self.n_tomo_lens))
            gaussCOSEBIgmgm_mix = np.zeros_like(gaussCOSEBIgmgm_sva)
            gaussCOSEBIgmgm_sn = np.zeros_like(gaussCOSEBIgmgm_sva)
            original_shape = gaussCOSEBIgmgm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**2*self.n_tomo_lens**2
            gaussELL_sva_flat = np.reshape(gaussELLgmgm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLgmgm_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gaussCOSEBIgmgm_sva[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_params_dict['survey_area_ggl']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBIgmgm_sva[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBIgmgm_sva[m_mode, n_mode, :, :, :, :, :, :]
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gaussCOSEBIgmgm_mix[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_params_dict['survey_area_ggl']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBIgmgm_mix[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBIgmgm_mix[m_mode, n_mode, :, :, :, :, :, :]
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    Tpm_product = self.Tn_p[m_mode](self.theta_gm)*self.Tn_p[n_mode](self.theta_gm) + self.Tn_m[m_mode](self.theta_gm)*self.Tn_m[n_mode](self.theta_gm)
                    integrand = (Tpm_product*self.theta_gm**2)[:,None, None]/self.dnpair_gm
                    aux_gm_sn = np.trapz(integrand,self.theta_gm,axis=0)/self.arcmin2torad2**2
                    gaussCOSEBIgmgm_sn[n_mode, m_mode, :, :, :, :, :, :] = (kron_delta_tomo_clust[None, None, :, None, :, None]
                                                                            * kron_delta_tomo_lens[None, None, None, :, None, :]) \
                                                                            * (survey_params_dict['ellipticity_dispersion'][None, :]**2*aux_gm_sn)[None, None, :, :, None, None]/2.
                    
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'gmgm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            gaussCOSEBIgmgm_sva = 0
            gaussCOSEBIgmgm_mix = 0
            gaussCOSEBIgmgm_sn = 0

        if self.gm and self.mm and self.cross_terms:
            gaussCOSEBImmgm_sn = 0
            gaussCOSEBImmgm_sva = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_clust, self.n_tomo_lens))
            gaussCOSEBImmgm_mix = np.zeros_like(gaussCOSEBImmgm_sva)
            original_shape = gaussCOSEBImmgm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**3*self.n_tomo_clust
            gaussELL_sva_flat = np.reshape(gaussELLmmgm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLmmgm_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    survey_area = max(survey_params_dict['survey_area_ggl'],survey_params_dict['survey_area_lens'])
                    gaussCOSEBImmgm_sva[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_area/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBImmgm_sva[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBImmgm_sva[m_mode, n_mode, :, :, :, :, :, :]
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gaussCOSEBImmgm_mix[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_area/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBImmgm_mix[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBImmgm_mix[m_mode, n_mode, :, :, :, :, :, :]
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'mmgm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            gaussCOSEBImmgm_sva = 0
            gaussCOSEBImmgm_mix = 0
            gaussCOSEBImmgm_sn = 0

        if self.mm:
            gaussCOSEBImmmm_sva = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_lens))
            gaussCOSEBImmmm_mix = np.zeros_like(gaussCOSEBImmmm_sva)
            gaussCOSEBImmmm_sn = np.zeros_like(gaussCOSEBImmmm_sva)
            original_shape = gaussCOSEBImmmm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**4
            gaussELL_sva_flat = np.reshape(gaussELLmmmm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLmmmm_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gaussCOSEBImmmm_sva[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_params_dict['survey_area_lens']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBImmmm_sva[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBImmmm_sva[m_mode, n_mode, :, :, :, :, :, :]
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gaussCOSEBImmmm_mix[m_mode, n_mode, :, :, :, :, :, :] = 1./2./np.pi/(survey_params_dict['survey_area_lens']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gaussCOSEBImmmm_mix[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBImmmm_mix[m_mode, n_mode, :, :, :, :, :, :]
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    Tpm_product = self.Tn_p[m_mode](self.theta_mm)*self.Tn_p[n_mode](self.theta_mm) + self.Tn_m[m_mode](self.theta_mm)*self.Tn_m[n_mode](self.theta_mm)
                    integrand = (Tpm_product*self.theta_mm**2)[:,None, None]/self.dnpair_mm
                    aux_mm_sn = np.trapz(integrand,self.theta_mm,axis=0)/self.arcmin2torad2**2
                    gaussCOSEBImmmm_sn[m_mode, n_mode, :, :, :, :, :, :] = (kron_delta_tomo_lens[None, None, :, None, :, None]
                                                                            * kron_delta_tomo_lens[None, None, None, :, None, :]
                                                                            + kron_delta_tomo_lens[None, None, :, None, None, :]
                                                                            * kron_delta_tomo_lens[None, None, None, :, :, None]) \
                                                                            * (survey_params_dict['ellipticity_dispersion']**2)[None, None, :, None, None, None] \
                                                                            * (survey_params_dict['ellipticity_dispersion']**2)[None, None, None, :, None, None] \
                                                                            * aux_mm_sn[None, None, :, :, None, None]/2.
                    gaussCOSEBImmmm_sn[n_mode, m_mode, :, :, :, :, :, :] = gaussCOSEBImmmm_sn[m_mode, n_mode, :, :, :, :, :, :] 
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'mmmm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            gaussCOSEBImmmm_sva = 0
            gaussCOSEBImmmm_mix = 0
            gaussCOSEBImmmm_sn = 0

        return gaussCOSEBIgggg_sva, gaussCOSEBIgggg_mix, gaussCOSEBIgggg_sn, \
            gaussCOSEBIgggm_sva, gaussCOSEBIgggm_mix, gaussCOSEBIgggm_sn, \
            gaussCOSEBIggmm_sva, gaussCOSEBIggmm_mix, gaussCOSEBIggmm_sn, \
            gaussCOSEBIgmgm_sva, gaussCOSEBIgmgm_mix, gaussCOSEBIgmgm_sn, \
            gaussCOSEBImmgm_sva, gaussCOSEBImmgm_mix, gaussCOSEBImmgm_sn, \
            gaussCOSEBImmmm_sva, gaussCOSEBImmmm_mix, gaussCOSEBImmmm_sn, \
    
    
    def covCOSEBI_non_gaussian(self,
                               obs_dict,
                               survey_params_dict,
                               output_dict,
                               bias_dict,
                               hod_dict,
                               prec,
                               tri_tab):
        if not self.cov_dict['nongauss']:
            return 0, 0, 0, 0, 0, 0
        else:
            return self.__covCOSEBI_4pt_projection(obs_dict,
                                                  survey_params_dict,
                                                  output_dict,
                                                  bias_dict,
                                                  hod_dict,
                                                  prec,
                                                  tri_tab,
                                                  True)

    def covCOSEBI_ssc(self,
                      obs_dict,
                      survey_params_dict,
                      output_dict,
                      bias_dict,
                      hod_dict,
                      prec,
                      tri_tab):
        if not self.cov_dict['ssc']:
            return 0, 0, 0, 0, 0, 0
        else:
            return self.__covCOSEBI_4pt_projection(obs_dict,
                                                  survey_params_dict,
                                                  output_dict,
                                                  bias_dict,
                                                  hod_dict,
                                                  prec,
                                                  tri_tab,
                                                  False)          

    def __covCOSEBI_4pt_projection(self,
                               obs_dict,
                               survey_params_dict,
                               output_dict,
                               bias_dict,
                               hod_dict,
                               prec,
                               tri_tab,
                               connected):

        nongaussCOSEBIgggg = None
        nongaussCOSEBIgggm = None
        nongaussCOSEBIggmm = None
        nongaussCOSEBIgmgm = None
        nongaussCOSEBImmgm = None
        nongaussCOSEBImmmm = None

        if (connected):
            nongaussELLgggg, nongaussELLgggm, nongaussELLggmm, nongaussELLgmgm, nongaussELLmmgm, nongaussELLmmmm = self.covELL_non_gaussian(
                obs_dict['ELLspace'], output_dict, bias_dict, hod_dict, prec, tri_tab)
        else:
            nongaussELLgggg, nongaussELLgggm, nongaussELLggmm, nongaussELLgmgm, nongaussELLmmgm, nongaussELLmmmm = self.covELL_ssc(
                bias_dict, hod_dict, prec, survey_params_dict, obs_dict['ELLspace'])
        

        if self.gg:
            nongaussCOSEBIgggg = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust))
            original_shape = nongaussCOSEBIgggg[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**4
            nongaussELL_flat = np.reshape(nongaussELLgggg, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongaussCOSEBIgggg[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(4.0*np.pi**2)*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    nongaussCOSEBIgggg[n_mode, m_mode, :, :, :, :, :, :] = nongaussCOSEBIgggg[m_mode, n_mode, :, :, :, :, :, :]
                    if connected:
                        nongaussCOSEBIgggg[n_mode, m_mode, :, :, :, :, :, :] /= (survey_params_dict['survey_area_clust'] / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'nonGaussian gggg term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            
            print("")
        else:
            nongaussCOSEBIgggg = 0
            

        if self.gg and self.gm and self.cross_terms:
            nongaussCOSEBIgggm = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust))
            original_shape = nongaussCOSEBIgggm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**3*self.n_tomo_lens
            nongaussELL_flat = np.reshape(nongaussELLgggm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongaussCOSEBIgggm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(4.0*np.pi**2)*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    nongaussCOSEBIgggm[n_mode, m_mode, :, :, :, :, :, :] = nongaussCOSEBIgggm[m_mode, n_mode, :, :, :, :, :, :]
                    if connected:
                        nongaussCOSEBIgggm[m_mode, n_mode, :, :, :, :, :, :] /= (max(survey_params_dict['survey_area_clust'],survey_params_dict['survey_area_ggl']) / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'nonGussian ggggm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            
            print("")
        else:
            nongaussCOSEBIgggm = 0

        if self.gg and self.mm and self.cross_terms:
            nongaussCOSEBIggmm = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust))
            original_shape = nongaussCOSEBIggmm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**2*self.n_tomo_clust**2
            nongaussELL_flat = np.reshape(nongaussELLggmm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongaussCOSEBIggmm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(4.0*np.pi**2)*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    nongaussCOSEBIggmm[n_mode, m_mode, :, :, :, :, :, :] = nongaussCOSEBIggmm[m_mode, n_mode, :, :, :, :, :, :]
                    if connected:
                        nongaussCOSEBIggmm[m_mode, n_mode, :, :, :, :, :, :] /= (max(survey_params_dict['survey_area_clust'],survey_params_dict['survey_area_lens']) / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'nonGussian ggmm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            
            print("")
        else:
            nongaussCOSEBIggmm = 0

        if self.gm:
            nongaussCOSEBIgmgm = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust))
            original_shape = nongaussCOSEBIgmgm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim**self.n_tomo_lens**2*self.n_tomo_clust**2
            nongaussELL_flat = np.reshape(nongaussELLgmgm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongaussCOSEBIgmgm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(4.0*np.pi**2)*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    nongaussCOSEBIgmgm[n_mode, m_mode, :, :, :, :, :, :] = nongaussCOSEBIgmgm[m_mode, n_mode, :, :, :, :, :, :]
                    if connected: 
                        nongaussCOSEBIgmgm[m_mode, n_mode, :, :, :, :, :, :] /= (survey_params_dict['survey_area_ggl']) / self.deg2torad2
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'nonGussian gmgm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            
            print("")
        else:
            nongaussCOSEBIgmgm = 0

        if self.gm and self.mm and self.cross_terms:
            nongaussCOSEBImmgm = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust))
            original_shape = nongaussCOSEBImmgm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**3*self.n_tomo_clust
            nongaussELL_flat = np.reshape(nongaussELLmmgm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, False)
                    nongaussCOSEBImmgm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(4.0*np.pi**2)*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    nongaussCOSEBImmgm[n_mode, m_mode, :, :, :, :, :, :] = nongaussCOSEBImmgm[m_mode, n_mode, :, :, :, :, :, :]
                    if connected:
                        nongaussCOSEBImmgm[m_mode, n_mode, :, :, :, :, :, :] /= (max(survey_params_dict['survey_area_ggl'],survey_params_dict['survey_area_lens']) / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'nonGussian mmgm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            
            print("")
        else:
            nongaussCOSEBImmgm = 0

        if self.mm:
            nongaussCOSEBImmmm = np.zeros(
                (self.En_modes, self.En_modes, self.sample_dim, self.sample_dim, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_lens))
            
            original_shape = nongaussCOSEBImmmm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**4
            nongaussELL_flat = np.reshape(nongaussELLmmmm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = self.En_modes*(self.En_modes + 1)/2
            for m_mode in range(self.En_modes):
                for n_mode in range(m_mode, self.En_modes):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongaussCOSEBImmmm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(4.0*np.pi**2)*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    nongaussCOSEBImmmm[n_mode, m_mode, :, :, :, :, :, :] = nongaussCOSEBImmmm[m_mode, n_mode, :, :, :, :, :, :]
                    if connected:
                        nongaussCOSEBImmmm[m_mode, n_mode, :, :, :, :, :, :] /= (survey_params_dict['survey_area_lens'] / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rCOSEBI E-mode covariance calculation for the '
                            'nonGussian mmmm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            
            print("")
            
        else:
            nongaussCOSEBImmmm = 0

        return nongaussCOSEBIgggg, nongaussCOSEBIgggm, nongaussCOSEBIggmm, nongaussCOSEBIgmgm, nongaussCOSEBImmgm, nongaussCOSEBImmmm
