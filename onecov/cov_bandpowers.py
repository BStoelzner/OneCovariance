import time
import numpy as np
from scipy.special import jv
from scipy.signal import argrelextrema
import multiprocessing as mp

import levin

try:
    from onecov.cov_theta_space import CovTHETASpace
except:
    from cov_theta_space import CovTHETASpace

def call_levin_many_args_WE(ells, ell_up, ell_lo, theta_range, T_of_theta, num_cores):
    """
    Auxillary function for the calculation of the weight functions for the bandpowers.
    Carries out the integrals over the Bessel functions in parallel for many arguments.
    
    Parameter
    ---------
    ells : array
        Fourier multipole (\ell) where the Weights should be evaluated at.
    ell_up : float
        Upper limit of the bandpower interval
    ell_lo : float
        Lower limit of the bandpower interval
    theta_range : array
        Theta range over which the Integration is carried out.
    T_of_theta : array
        Window function to select theta range over which the band power is estimated.
        We use a Hann window by default. Must have the same length as theta_range.
    num_cores : array
        Number of cores used for the computation. 
    
    Returns
    -------
    result_WEE, result_WEB, result_WnE : arrays
        The 3 weight for bandpower in a single ell_band but at all ells.
        Have the same length as ells

    """
    
    global call_levin_WEE
    def call_levin_WEE(i_ell):
        lev = levin.Levin(2, 16, 32, 1e-6, 50)
        lev.init_integral(theta_range, T_of_theta[:,None], True, False) 
        result = ell_up*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 0, 1, theta_range[0], theta_range[-1]))
        result -=ell_lo*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 0, 1, theta_range[0], theta_range[-1]))
        result -=ell_lo*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 4, 1, theta_range[0], theta_range[-1]))
        result +=ell_up*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 4, 1, theta_range[0], theta_range[-1]))
        lev.init_integral(theta_range, (T_of_theta/theta_range)[:,None], True, False)
        result -=8.0*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 4, 2, theta_range[0], theta_range[-1]))
        result +=8.0*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 4, 2, theta_range[0], theta_range[-1]))
        lev.init_integral(theta_range, (T_of_theta/theta_range**2)[:,None], True, False)
        result -=8.0/ell_up*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 4, 1, theta_range[0], theta_range[-1]))
        result +=8.0/ell_lo*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 4, 1, theta_range[0], theta_range[-1]))
        return result
    
    global call_levin_WEB
    def call_levin_WEB(i_ell):
        lev = levin.Levin(2, 16, 32, 1e-6, 50)
        lev.init_integral(theta_range, T_of_theta[:,None], True, False)
        result = ell_up*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 0, 1, theta_range[0], theta_range[-1]))
        result -=ell_lo*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 0, 1, theta_range[0], theta_range[-1]))
        result +=ell_lo*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 4, 1, theta_range[0], theta_range[-1]))
        result -=ell_up*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 4, 1, theta_range[0], theta_range[-1]))
        lev.init_integral(theta_range, (T_of_theta/theta_range)[:,None], True, True)
        result +=8.0*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 4, 2, theta_range[0], theta_range[-1]))
        result -=8.0*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 4, 2, theta_range[0], theta_range[-1]))
        lev.init_integral(theta_range, (T_of_theta/theta_range**2)[:,None], True, True)
        result +=8.0/ell_up*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 4, 1, theta_range[0], theta_range[-1]))
        result -=8.0/ell_lo*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 4, 1, theta_range[0], theta_range[-1]))
        return result
    
    global call_levin_WnE
    def call_levin_WnE(i_ell):
        lev = levin.Levin(2, 16, 32, 1e-6, 50)
        lev.init_integral(theta_range, T_of_theta[:,None], True, False) 
        result = -ell_up*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 2, 1, theta_range[0], theta_range[-1]))
        result +=ell_lo*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 2, 1, theta_range[0], theta_range[-1]))
        lev.init_integral(theta_range, (T_of_theta/theta_range)[:,None], True, False)
        result -=2.0*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_up, 2, 0, theta_range[0], theta_range[-1]))
        result +=2.0*np.nan_to_num(lev.double_bessel(
            ells[i_ell], ell_lo, 2, 0, theta_range[0], theta_range[-1]))
        return result

    pool = mp.Pool(num_cores)
    result_WEE = np.array(pool.map(
                call_levin_WEE, [i for i in range(len(ells))]))[:,0]
    pool.close()
    pool.terminate()
    pool = mp.Pool(num_cores)
    result_WEB = np.array(pool.map(
                call_levin_WEB, [i for i in range(len(ells))]))[:,0]
    pool.close()
    pool.terminate()

    pool = mp.Pool(num_cores)
    result_WnE = np.array(pool.map(
                call_levin_WnE, [i for i in range(len(ells))]))[:,0]
    pool.close()
    pool.terminate()

    
    return result_WEE, result_WEB, result_WnE


class CovBandPowers(CovTHETASpace):
    """
    This class calculates the bandpower covariance for all probes specified.
    The calculations are carried out using the realspace covariance. All
    functionality from CovTHETASpace is inherited. The bandpower covariance
    is, however, calculated from ell space.

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
        'bandpowers' : dictionary
            Specifies the exact details for the bandpower covariance.
    cosmo_dict : dictionary
        Specifies all cosmological parameters. To be passed from the
        read_input method of the Input class.
    bias_dict : dictionary
        Specifies all the information about the bias model. To be passed
        from the read_input method of the Input class.
    iA_dict: dictionary
        Specifies all the information about the intrinsic alignment model.
        To be passed from the read_input method in the Input class.
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
        'tri': dictionary
            Look-up table for the trispectra (for all combinations of
            matter 'm' and tracer 'g', optional).
            Possible keys: '', 'z', 'mmmm', 'mmgm', 'gmgm', 'ggmm',
            'gggm', 'gggg'

    Attributes:
    -----------
    see CovELLSpace class

    Example :
    ---------
    from src.cov_input import Input, FileInput
    from src.cov_theta_space import CovBandPowers
    inp = Input()
    covterms, observables, output, cosmo, bias, iA hod, survey_params, \
        prec = inp.read_input()
    fileinp = FileInput()
    read_in_tables = fileinp.read_input(inp.config_name)
    covBP = CovBandPowers(covterms, observables, output, cosmo, bias,
        iA, hod, survey_params, prec, read_in_tables)

    """

    def __init__(self,
                 cov_dict,
                 obs_dict,
                 output_dict,
                 cosmo_dict,
                 bias_dict,
                 iA_dict,
                 hod_dict,
                 survey_params_dict,
                 prec,
                 read_in_tables):
        self.delta_ln_theta = obs_dict['bandpowers']['apodisation_log_width']
        obs_dict['THETAspace']['theta_min'] = np.exp(np.log(obs_dict['bandpowers']['theta_lo']) - self.delta_ln_theta/2)
        obs_dict['THETAspace']['theta_max'] = np.exp(np.log(obs_dict['bandpowers']['theta_up']) + self.delta_ln_theta/2)
        obs_dict['THETAspace']['theta_bins'] = obs_dict['bandpowers']['theta_binning']
        obs_dict['THETAspace']['theta_type'] = 'log'
        obs_dict['THETAspace']['xi_pp'] = True
        obs_dict['THETAspace']['xi_mm'] = True
        self.cross_terms = True
        CovTHETASpace.__init__(self,
                             cov_dict,
                             obs_dict,
                             output_dict,
                             cosmo_dict,
                             bias_dict,
                             iA_dict,
                             hod_dict,
                             survey_params_dict,
                             prec,
                             read_in_tables)
        self.__get_Hann_window(obs_dict)
        self.__set_multipoles(obs_dict['bandpowers'])
        self.__get_gpm()
        self.__get_norm()
        self.levin_int = levin.Levin(2, 16, 32, obs_dict['bandpowers']['bandpower_accuracy'], self.integration_intervals)
        self.delta_theta = self.theta_ul_bins[1:] - self.theta_ul_bins[:-1]
        self.dnpair_gg, self.dnpair_gm, self.dnpair_mm, self.theta_gg, self.theta_gm, self.theta_mm  = self.get_dnpair([self.gg, self.gm, self.mm],
                                                                                                                        self.thetabins,
                                                                                                                        survey_params_dict,
                                                                                                                        read_in_tables['npair'])
        
        self.__get_shotnoise_integrals()
        self.__get_WXY()
        self.levin_int.init_w_ell(self.ell_fourier_integral, self.WXY_stack.T)
        self.ell_limits = []
        for mode in range(len(self.ell_bins)):
            limits_at_mode = np.array(self.ell_fourier_integral[argrelextrema(self.WXY_stack[mode, :], np.less)[0][:]])
            limits_at_mode_append = np.zeros(len(limits_at_mode) + 2)
            limits_at_mode_append[1:-1] = limits_at_mode
            limits_at_mode_append[0] = self.ellrange[0]
            limits_at_mode_append[-1] = self.ellrange[-1]
            self.ell_limits.append(limits_at_mode_append)
        
        
    def __set_multipoles(self,
                         covbandpowersettings):
        """
        Calculates the (bandpower) multioples at which the covariance is calculated

        Parameters
        ----------
        covbandpowersettings : dictionary
            Specifies the multipoles at which the covariance for bandpowers
            is evaluated.

        Returns
        -------
        ellrange : array
            with shape (ell bins)

        """

        if covbandpowersettings['ell_type'] == 'lin':
            ell_ul_bins = np.linspace(
                covbandpowersettings['ell_min'],
                covbandpowersettings['ell_max'],
                covbandpowersettings['ell_bins'] + 1)
            ell_bins = .5 * (ell_ul_bins[1:] + ell_ul_bins[:-1])
        else:
            ell_ul_bins = np.geomspace(
                covbandpowersettings['ell_min'],
                covbandpowersettings['ell_max'],
                covbandpowersettings['ell_bins'] + 1)
            ell_bins = np.exp(.5 * (np.log(ell_ul_bins[1:])
                                    + np.log(ell_ul_bins[:-1])))
        self.ell_bins = ell_bins
        self.ell_ul_bins = ell_ul_bins
        self.ell_fourier_integral = np.geomspace(self.ellrange[0]-1, self.ellrange[-1]+1,800)
    
    def __get_Hann_window(self,
                           obs_dict):
        """
        Precomputes the Hann window for the apodisation, yielding the function
        T(theta).
        """
        self.log_theta_bins = np.log(self.thetabins)
        self.T_of_theta = np.zeros(len(self.thetabins))
        xlo = np.log(obs_dict['bandpowers']['theta_lo'])
        xup = np.log(obs_dict['bandpowers']['theta_up'])
        for i_theta in range(len(self.thetabins)):
            x = self.log_theta_bins[i_theta]
            if x < xlo + self.delta_ln_theta/2.0:
                self.T_of_theta[i_theta] = np.cos(np.pi/2.*((x - (xlo + self.delta_ln_theta/2.))/self.delta_ln_theta))**2.0
            else:
                if x >= xlo + self.delta_ln_theta/2.0 and x < xup - self.delta_ln_theta/2.0: 
                    self.T_of_theta[i_theta] = 1.0
                else:
                    self.T_of_theta[i_theta] = np.cos(np.pi/2.*((x - (xup - self.delta_ln_theta/2.))/self.delta_ln_theta))**2.0

    def __get_WXY(self):
        """
        Function precomputing bandpower weight functions WEE, WEB and WnE for later integration
        """
        self.Wl_EE = np.zeros((len(self.ell_bins), len(self.ell_fourier_integral)))
        self.Wl_EB = np.zeros((len(self.ell_bins), len(self.ell_fourier_integral)))
        self.Wl_nE = np.zeros((len(self.ell_bins), len(self.ell_fourier_integral)))
        for i_ell in range(len(self.ell_bins)):    
            self.Wl_EE[i_ell, :], self.Wl_EB[i_ell, :], self.Wl_nE[i_ell, :] = call_levin_many_args_WE(self.ell_fourier_integral,
                                                                              self.ell_ul_bins[i_ell+1],
                                                                              self.ell_ul_bins[i_ell],
                                                                              self.thetabins/60/180*np.pi,
                                                                              self.T_of_theta,
                                                                              self.num_cores)
        self.WXY_stack = np.zeros((3*len(self.ell_bins), len(self.ell_fourier_integral)))
        self.WXY_stack[:len(self.ell_bins), : ] = self.Wl_EE
        self.WXY_stack[len(self.ell_bins):2*len(self.ell_bins), : ] = self.Wl_EB
        self.WXY_stack[2*len(self.ell_bins):, : ] = self.Wl_nE
        
    def __get_shotnoise_integrals(self):
        """
        Function precomputing the integrals for the shot/shape noise over theta
        """
        self.SN_integral_gggg = np.zeros((len(self.ell_bins), len(self.ell_bins), self.n_tomo_clust, self.n_tomo_clust))
        self.SN_integral_gmgm = np.zeros((len(self.ell_bins), len(self.ell_bins), self.n_tomo_clust, self.n_tomo_lens))
        self.SN_integral_mmmm = np.zeros((len(self.ell_bins), len(self.ell_bins), self.n_tomo_lens, self.n_tomo_lens))
        if self.gg:
            original_shape = (self.n_tomo_clust, self.n_tomo_clust)
            dnpair_gg_flat = np.reshape(self.dnpair_gg, (len(self.theta_gg), self.n_tomo_clust**2))
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    L1up = self.ell_ul_bins[m_mode + 1]
                    L2up = self.ell_ul_bins[n_mode + 1]
                    L1lo = self.ell_ul_bins[m_mode]
                    L2lo = self.ell_ul_bins[n_mode]
                    integrand = (self.T_of_theta**2)[:,None]/(dnpair_gg_flat* 60*180/np.pi)
                    self.levin_int.init_integral(self.theta_gg/60/180*np.pi, integrand, True, True)
                    result = L1up*L2up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 1, 1, self.theta_gg[0]/60/180*np.pi, self.theta_gg[-1]/60/180*np.pi))
                    result -= L1up*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 1, 1, self.theta_gg[0]/60/180*np.pi, self.theta_gg[-1]/60/180*np.pi))
                    result -= L1lo*L2up*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 1, 1, self.theta_gg[0]/60/180*np.pi, self.theta_gg[-1]/60/180*np.pi))
                    result += L1lo*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 1, 1, self.theta_gg[0]/60/180*np.pi, self.theta_gg[-1]/60/180*np.pi))
                    self.SN_integral_gggg[m_mode, n_mode, :, :] = np.reshape(np.array(result), original_shape)

        if self.gm:
            original_shape = (self.n_tomo_clust, self.n_tomo_lens)
            dnpair_gm_flat = np.reshape(self.dnpair_gm, (len(self.theta_gm), self.n_tomo_clust*self.n_tomo_lens))

            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    L1up = self.ell_ul_bins[m_mode + 1]
                    L2up = self.ell_ul_bins[n_mode + 1]
                    L1lo = self.ell_ul_bins[m_mode]
                    L2lo = self.ell_ul_bins[n_mode]
                    integrand = (self.T_of_theta**2)[:,None]/(dnpair_gm_flat* 60*180/np.pi)
                    self.levin_int.init_integral(self.theta_gm/60/180*np.pi, integrand, True, True)
                    result = L1up*L2up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 1, 1, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result -= L1up*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 1, 1, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result -= L1lo*L2up*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 1, 1, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result += L1lo*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 1, 1, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    integrand /= self.theta_gm[:,None]/60/180*np.pi
                    self.levin_int.init_integral(self.theta_gm/60/180*np.pi, integrand, True, True)
                    result += 2.*L1up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 1, 0, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result += 2.*L2up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 0, 1, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result -= 2.*L1up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 1, 0, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result -= 2.*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 0, 1, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result -= 2.*L1lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 1, 0, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result -= 2.*L2up*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 0, 1, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result += 2.*L1lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 1, 0, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result += 2.*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 0, 1, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    integrand /= self.theta_gm[:,None]/60/180*np.pi
                    self.levin_int.init_integral(self.theta_gm/60/180*np.pi, integrand, True, True)
                    result += 4.*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 0, 0, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result -= 4.*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 0, 0, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result -= 4.*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 0, 0, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    result += 4.*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 0, 0, self.theta_gm[0]/60/180*np.pi, self.theta_gm[-1]/60/180*np.pi))
                    self.SN_integral_gmgm[m_mode, n_mode, :, :] = np.reshape(np.array(result), original_shape)
        
        if self.mm:
            original_shape = (self.n_tomo_lens, self.n_tomo_lens)
            dnpair_mm_flat = np.reshape(self.dnpair_mm, (len(self.theta_mm), self.n_tomo_lens**2))
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    L1up = self.ell_ul_bins[m_mode + 1]
                    L2up = self.ell_ul_bins[n_mode + 1]
                    L1lo = self.ell_ul_bins[m_mode]
                    L2lo = self.ell_ul_bins[n_mode]
                    integrand = (self.T_of_theta**2)[:,None]/(dnpair_mm_flat * 60*180/np.pi)
                    self.levin_int.init_integral(self.theta_mm/60/180*np.pi, integrand, True, True)
                    result = L1up*L2up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= L1up*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= L1lo*L2up*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += L1lo*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result *= 2
                    integrand /= self.theta_mm[:,None]/60/180*np.pi
                    self.levin_int.init_integral(self.theta_mm/60/180*np.pi, integrand, True, True)
                    result -= 8.*L2up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 2, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 8.*L1up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 1, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 8.*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 2, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 8.*L1up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 1, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 8.*L2up*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 2, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 8.*L1lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 1, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 8.*L2lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 2, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 8.*L1lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 1, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    integrand /= self.theta_mm[:,None]/60/180*np.pi
                    self.levin_int.init_integral(self.theta_mm/60/180*np.pi, integrand, True, True)
                    result -= 8.*(L2up/L1up + L1up/L2up)*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 8.*(L2lo/L1up + L1up/L2lo)*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 8.*(L2up/L1lo + L1lo/L2up)*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 8.*(L2lo/L1lo + L1lo/L2lo)*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 64.*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 2, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 64.*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 2, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 64.*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 2, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 64.*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 2, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    integrand /= self.theta_mm[:,None]/60/180*np.pi
                    self.levin_int.init_integral(self.theta_mm/60/180*np.pi, integrand, True, True)
                    result += 64./L2up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 2, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 64./L1up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 1, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 64./L2lo*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 2, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 64./L1up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 1, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 64./L2up*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 2, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 64./L1lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 1, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 64./L2lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 2, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 64./L1lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 1, 2, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    integrand /= self.theta_mm[:,None]/60/180*np.pi
                    self.levin_int.init_integral(self.theta_mm/60/180*np.pi, integrand, True, True)
                    result += 64./L1up/L2up*np.nan_to_num(self.levin_int.double_bessel(L1up, L2up, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 64./L1up/L2lo*np.nan_to_num(self.levin_int.double_bessel(L1up, L2lo, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result -= 64./L1lo/L2up*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2up, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    result += 64./L1lo/L2lo*np.nan_to_num(self.levin_int.double_bessel(L1lo, L2lo, 1, 1, self.theta_mm[0]/60/180*np.pi, self.theta_mm[-1]/60/180*np.pi))
                    self.SN_integral_mmmm[m_mode, n_mode, :, :] = np.reshape(np.array(result), original_shape)
                  

    def __get_gpm(self):
        """
        Precomputes the bandpower kernels and stores them in private
        variables
        """
        self.g_plus = np.zeros((len(self.ell_bins), len(self.thetabins)))
        self.g_minus = np.zeros((len(self.ell_bins), len(self.thetabins)))
        self.h_ell = np.zeros((len(self.ell_bins), len(self.thetabins)))
        for i_theta in range(len(self.thetabins)):
            for i_ell in range(len(self.ell_bins)):
                theta_times_ell_lo = self.thetabins[i_theta]*self.ell_ul_bins[i_ell]/60/180*np.pi
                theta_times_ell_up = self.thetabins[i_theta]*self.ell_ul_bins[i_ell+1]/60/180*np.pi
                curly_G_minus_up = (theta_times_ell_up - 8./theta_times_ell_up)*jv(1, theta_times_ell_up) - 8*jv(2, theta_times_ell_up)
                curly_G_minus_lo = (theta_times_ell_lo - 8./theta_times_ell_lo)*jv(1, theta_times_ell_lo) - 8*jv(2, theta_times_ell_lo)
                self.g_plus[i_ell,i_theta] = 1./(self.thetabins[i_theta]/60/180*np.pi)**2*(theta_times_ell_up*jv(1, theta_times_ell_up) - theta_times_ell_lo*jv(1, theta_times_ell_lo))
                self.g_minus[i_ell,i_theta] = 1./(self.thetabins[i_theta]/60/180*np.pi)**2*(curly_G_minus_up - curly_G_minus_lo)
                self.h_ell[i_ell,i_theta] = - 1./(self.thetabins[i_theta]/60/180*np.pi)**2*(theta_times_ell_up*jv(1, theta_times_ell_up) - theta_times_ell_lo*jv(1, theta_times_ell_lo) + 2.*jv(0, theta_times_ell_up) - 2.*jv(0, theta_times_ell_lo))  

    def __get_norm(self):
        """
        Precomputes the normalisation for the band powers
        """
        self.N_ell = np.log(self.ell_ul_bins[1:]/self.ell_ul_bins[:-1])

    def __project_from_theta_to_ell(self,
                                    weight1,
                                    weight2,
                                    covariance_theta):
        """
        Projects real space covariances to bandpower covariances using two weights and the corresponding
        covariance in theta space.
        """
        if type(covariance_theta) is np.ndarray:
            theta_terms = (self.thetabins/60/180*np.pi * self.T_of_theta * self.delta_theta/60/180*np.pi)[:, None] *(self.thetabins/60/180*np.pi * self.T_of_theta * self.delta_theta/60/180*np.pi)[None, :]
            weight_terms = weight1[:,None, :, None]*weight2[None, :, None, :]
            all_terms = covariance_theta[None, None, :, :, :, :, :, :, :, :] * weight_terms[:,:,:,:, None, None, None, None, None, None] * theta_terms[None, None, :, :, None, None, None, None, None, None]
            return np.pi**2/self.N_ell[:, None, None, None, None, None, None, None]/self.N_ell[None, :, None, None, None, None, None, None] * np.sum(all_terms, axis = (2,3))
        else:
            return 0.0
   
    def calc_covbandpowers(self,
                           obs_dict,
                            output_dict,
                            bias_dict,
                            hod_dict,
                            survey_params_dict,
                            prec,
                            read_in_tables):
        """
        Calculates the full covariance between all observables for bandpowers
        as specified in the config file.

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
            'tri': dictionary
                Look-up table for the trispectra (for all combinations of
                matter 'm' and tracer 'g', optional).
                Possible keys: '', 'z', 'mmmm', 'mmgm', 'gmgm', 'ggmm',
                'gggm', 'gggg'

        Returns
        -------
        gauss, nongauss, ssc : list of arrays
            each with 10 entries for the observables
                ['ww', 'wgt', 'wxi+', 'wxi-', 'gtgt', 'xi+gt',
                 'xigt-', 'xi+xi+', 'xi+xi-', 'xi-xi-']
            each entry with shape (theta bins, theta bins,
                                   sample bins, sample bins,
                                   no_tomo_clust\lens, no_tomo_clust\lens,
                                   no_tomo_clust\lens, no_tomo_clust\lens)
        """

        if not self.cov_dict['split_gauss']:
            gauss_CEgggg, gauss_CEgggm, gauss_CEggmm, gauss_CBggmm, \
                gauss_CEgmgm, gauss_CEmmgm, gauss_CBmmgm, \
                gauss_CEEmmmm, gauss_CEBmmmm, \
                gauss_CBBmmmm, \
                gauss_CEgggg_sn, gauss_CEgmgm_sn, gauss_CEEmmmm_sn, gauss_CBBmmmm_sn = \
                self.covbandpowers_gaussian(obs_dict,
                                       survey_params_dict)
            gauss = [gauss_CEgggg + gauss_CEgggg_sn, gauss_CEgggm, gauss_CEggmm, gauss_CBggmm,
                     gauss_CEgmgm + gauss_CEgmgm_sn, gauss_CEmmgm, gauss_CBmmgm,
                     gauss_CEEmmmm + gauss_CEEmmmm_sn, gauss_CEBmmmm,
                     gauss_CBBmmmm + gauss_CBBmmmm_sn]
        else:
            gauss = self.covbandpowers_gaussian(obs_dict,
                                       survey_params_dict)
        
        nongauss = self.covbandpowers_non_gaussian(obs_dict['ELLspace'],
                                              survey_params_dict,
                                              output_dict,
                                              bias_dict,
                                              hod_dict,
                                              prec,
                                              read_in_tables['tri'])

        ssc = self.covbandpowers_ssc(obs_dict['ELLspace'],
                                survey_params_dict,
                                output_dict,
                                bias_dict,
                                hod_dict,
                                prec,
                                read_in_tables['tri'])

        return list(gauss), list(nongauss), list(ssc)

    def covbandpowers_gaussian(self,
                               obs_dict,
                               survey_params_dict):
        """
        Calculates the Gaussian (disconnected) covariance for bandpowers
        for the all specified observables.

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
            'bandpowers' : dictionary
                Specifies the exact details for the bandpower covariance.
        survey_params_dict : dictionary
            Specifies all the information unique to a specific survey.
            Relevant values are the effective number density of galaxies
            for all tomographic bins as well as the ellipticity
            dispersion for galaxy shapes. To be passed from the
            read_input method of the Input class.
        
        Returns
        -------
        Depending whether split_gaussian is true or not.
        split_gauss == True:
            gauss_BPgggg_sva, gauss_BPgggg_mix, gauss_BPgggg_sn, \
            gauss_BPgggm_sva, gauss_BPgggm_mix, gauss_BPgggm_sn, \
            gauss_BPEggmm_sva, gauss_BPEggmm_mix, gauss_BPEggmm_sn, \
            gauss_BPBggmm_sva, gauss_BPBggmm_mix, gauss_BPBggmm_sn, \
            gauss_BPgmgm_sva, gauss_BPgmgm_mix, gauss_BPgmgm_sn, \
            gauss_BPEmmgm_sva, gauss_BPEmmgm_mix, gauss_BPEmmgm_sn, \
            gauss_BPBmmgm_sva, gauss_BPBmmgm_mix, gauss_BPBmmgm_sn, \
            gauss_BPEEmmmm_sva, gauss_BPEEmmmm_mix, gauss_BPEEmmmm_sn, \
            gauss_BPEBmmmm_sva, gauss_BPEBmmmm_mix, gauss_BPEBmmmm_sn, \
            gauss_BPBBmmmm_sva, gauss_BPBBmmmm_mix, gauss_BPBBmmmm_sn : list of arrays
            
            each with shape (ell bins, ell bins,
                             sample bins, sample bins,
                             n_tomo_clust/lens, n_tomo_clust/lens,
                             n_tomo_clust/lens, n_tomo_clust/lens)
        split_gauss == False
            gauss_BPgggg, gauss_BPgggm, gauss_BPEggmm, gauss_BPBggmm, \
            gauss_BPgmgm, gauss_BPEmmgm, gauss_BPBmmgm, \
            gauss_BPEEmmmm, gauss_BPEBmmmm, \
            gauss_BPBBmmmm, \
            gauss_BPgggg_sn, gauss_BPgmgm_sn, gauss_BPEEmmmm_sn, gauss_BPBBmmmm_sn

            each with shape (ell bins, ell bins,
                             sample bins, sample bins,
                             n_tomo_clust/lens, n_tomo_clust/lens,
                             n_tomo_clust/lens, n_tomo_clust/lens)
        Note :
        ------
        The shot-noise terms are denoted with '_sn'. To get the full
        covariance contribution to the diagonal terms of the covariance
        matrix, one needs to add gauss_xy + gauss_xy_sn. They
        are kept separated.

        """

        if not self.cov_dict['gauss']:
            return 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

        print("Calculating gaussian bandpower covariance from angular " +
              "correlations.")

        gauss_BPgggg_sva, gauss_BPgggg_mix, gauss_BPgggg_sn, \
            gauss_BPgggm_sva, gauss_BPgggm_mix, gauss_BPgggm_sn, \
            gauss_BPEggmm_sva, gauss_BPEggmm_mix, gauss_BPEggmm_sn, \
            gauss_BPBggmm_sva, gauss_BPBggmm_mix, gauss_BPBggmm_sn, \
            gauss_BPgmgm_sva, gauss_BPgmgm_mix, gauss_BPgmgm_sn, \
            gauss_BPEmmgm_sva, gauss_BPEmmgm_mix, gauss_BPEmmgm_sn, \
            gauss_BPBmmgm_sva, gauss_BPBmmgm_mix, gauss_BPBmmgm_sn, \
            gauss_BPEEmmmm_sva, gauss_BPEEmmmm_mix, gauss_BPEEmmmm_sn, \
            gauss_BPEBmmmm_sva, gauss_BPEBmmmm_mix, gauss_BPEBmmmm_sn, \
            gauss_BPBBmmmm_sva, gauss_BPBBmmmm_mix, gauss_BPBBmmmm_sn = \
            self.__covbandpowers_split_gaussian(obs_dict,
                                           survey_params_dict)

        if not self.cov_dict['split_gauss']:
            gauss_BPgggg = gauss_BPgggg_sva + gauss_BPgggg_mix
            gauss_BPgggm = gauss_BPgggm_sva + gauss_BPgggm_mix
            gauss_BPEggmm = gauss_BPEggmm_sva + gauss_BPEggmm_mix
            gauss_BPBggmm = gauss_BPBggmm_sva + gauss_BPBggmm_mix
            gauss_BPgmgm = gauss_BPgmgm_sva + gauss_BPgmgm_mix
            gauss_BPEmmgm = gauss_BPEmmgm_sva + gauss_BPEmmgm_mix
            gauss_BPBmmgm = gauss_BPBmmgm_sva + gauss_BPBmmgm_mix
            gauss_BPEEmmmm = gauss_BPEEmmmm_sva + gauss_BPEEmmmm_mix
            gauss_BPEBmmmm = gauss_BPEBmmmm_sva + gauss_BPEBmmmm_mix
            gauss_BPBBmmmm = gauss_BPBBmmmm_sva + gauss_BPBBmmmm_mix
            return gauss_BPgggg, gauss_BPgggm, gauss_BPEggmm, gauss_BPBggmm, \
                gauss_BPgmgm, gauss_BPEmmgm, gauss_BPBmmgm, \
                gauss_BPEEmmmm, gauss_BPEBmmmm, \
                gauss_BPBBmmmm, \
                gauss_BPgggg_sn, gauss_BPgmgm_sn, gauss_BPEEmmmm_sn, gauss_BPBBmmmm_sn
        else:
            return gauss_BPgggg_sva, gauss_BPgggg_mix, gauss_BPgggg_sn, \
                    gauss_BPgggm_sva, gauss_BPgggm_mix, gauss_BPgggm_sn, \
                    gauss_BPEggmm_sva, gauss_BPEggmm_mix, gauss_BPEggmm_sn, \
                    gauss_BPBggmm_sva, gauss_BPBggmm_mix, gauss_BPBggmm_sn, \
                    gauss_BPgmgm_sva, gauss_BPgmgm_mix, gauss_BPgmgm_sn, \
                    gauss_BPEmmgm_sva, gauss_BPEmmgm_mix, gauss_BPEmmgm_sn, \
                    gauss_BPBmmgm_sva, gauss_BPBmmgm_mix, gauss_BPBmmgm_sn, \
                    gauss_BPEEmmmm_sva, gauss_BPEEmmmm_mix, gauss_BPEEmmmm_sn, \
                    gauss_BPEBmmmm_sva, gauss_BPEBmmmm_mix, gauss_BPEBmmmm_sn, \
                    gauss_BPBBmmmm_sva, gauss_BPBBmmmm_mix, gauss_BPBBmmmm_sn

    def __covbandpowers_split_gaussian(self,
                                       obs_dict,
                                       survey_params_dict):
        """
        Calculates the Gaussian (disconnected) covariance for band powers
        for the specified observables and splits it into sample-variance
        (SVA), shot noise (SN) and SNxSVA(mix) terms.

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
            'bandpowers' : dictionary
                Specifies the exact details for the bandpower covariance.
        survey_params_dict : dictionary
            Specifies all the information unique to a specific survey.
            Relevant values are the effective number density of galaxies
            for all tomographic bins as well as the ellipticity
            dispersion for galaxy shapes. To be passed from the
            read_input method of the Input class.
        calc_prefac : boolean
            Specifies whether the ell-independent prefactor should be multiplied
            or not. Is set to True by default.
        
        
        
        Returns:
        --------
            gauss_BPgggg_sva, gauss_BPgggg_mix, gauss_BPgggg_sn, \
            gauss_BPgggm_sva, gauss_BPgggm_mix, gauss_BPgggm_sn, \
            gauss_BPEggmm_sva, gauss_BPEggmm_mix, gauss_BPEggmm_sn, \
            gauss_BPBggmm_sva, gauss_BPBggmm_mix, gauss_BPBggmm_sn, \
            gauss_BPgmgm_sva, gauss_BPgmgm_mix, gauss_BPgmgm_sn, \
            gauss_BPEmmgm_sva, gauss_BPEmmgm_mix, gauss_BPEmmgm_sn, \
            gauss_BPBmmgm_sva, gauss_BPBmmgm_mix, gauss_BPBmmgm_sn, \
            gauss_BPEEmmmm_sva, gauss_BPEEmmmm_mix, gauss_BPEEmmmm_sn, \
            gauss_BPEBmmmm_sva, gauss_BPEBmmmm_mix, gauss_BPEBmmmm_sn, \
            gauss_BPBBmmmm_sva, gauss_BPBBmmmm_mix, gauss_BPBBmmmm_sn : list of arrays
            
            each with shape (ell bins, ell bins,
                            sample bins, sample bins,
                            n_tomo_clust/lens, n_tomo_clust/lens,
                            n_tomo_clust/lens, n_tomo_clust/lens)
        """

        if not self.cov_dict['gauss']:
            return 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, \
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
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
        if self.gg or self.gm:
            kron_delta_tomo_clust = np.diag(np.ones(self.n_tomo_clust))
        if self.mm or self.gm:
            kron_delta_tomo_lens = np.diag(np.ones(self.n_tomo_lens))

        if self.gg:
            gauss_BPgggg_sva = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust))
            gauss_BPgggg_mix = np.zeros_like(gauss_BPgggg_sva)
            gauss_BPgggg_sn = np.zeros_like(gauss_BPgggg_sva)
            original_shape = gauss_BPgggg_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**4
            gaussELL_sva_flat = np.reshape(gaussELLgggg_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLgggg_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPgggg_sva[m_mode, n_mode, :, :, :, :, :, :] = 2.*np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPgggg_mix[m_mode, n_mode, :, :, :, :, :, :] = 2.*np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    
                    gauss_BPgggg_sn[n_mode, m_mode, :, :, :, :, :, :] = np.pi**2/self.N_ell[m_mode]/self.N_ell[n_mode]*(kron_delta_tomo_clust[None, None, :, None, :, None]
                                                                            * kron_delta_tomo_clust[None, None, None, :, None, :]
                                                                            + kron_delta_tomo_clust[None, None, :, None, None, :]
                                                                            * kron_delta_tomo_clust[None, None, None, :, :, None]) \
                                                                            * (np.ones(self.n_tomo_clust)[None, :]**2*np.ones(self.n_tomo_clust)[:, None]**2)[None, None, :, :, None, None]*self.SN_integral_gggg[m_mode, n_mode, None, None, :, : ,None, None] 
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rBand power covariance calculation for the Gaussian '
                            'gggg term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            gauss_BPgggg_sva, gauss_BPgggg_mix, gauss_BPgggg_sn = 0, 0, 0

        if self.gg and self.gm and self.cross_terms:
            gauss_BPgggm_sva = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_lens))
            gauss_BPgggm_mix = np.zeros_like(gauss_BPgggm_sva)
            original_shape = gauss_BPgggm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**3*self.n_tomo_lens
            gaussELL_sva_flat = np.reshape(gaussELLgggm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLgggm_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPgggm_sva[m_mode, n_mode, :, :, :, :, :, :] = 2.*np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, 2*len(self.ell_bins) + n_mode)),original_shape)
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPgggm_mix[m_mode, n_mode, :, :, :, :, :, :] = 2.*np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, 2*len(self.ell_bins) + n_mode)),original_shape)
                    
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rBand power covariance calculation for the Gaussian '
                            'gggm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
                    gauss_BPgggm_sn = 0
            print("")
        else:
            gauss_BPgggm_sva, gauss_BPgggm_mix, gauss_BPgggm_sn = 0, 0, 0

        if self.gg and self.mm and self.cross_terms:
            gauss_BPEggmm_sva = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_lens, self.n_tomo_lens))
            gauss_BPBggmm_sva = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_lens, self.n_tomo_lens))  
            original_shape = gauss_BPEggmm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**2*self.n_tomo_lens**2
            gaussELL_sva_flat = np.reshape(gaussELLggmm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPEggmm_sva[m_mode, n_mode, :, :, :, :, :, :] = np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gauss_BPBggmm_sva[m_mode, n_mode, :, :, :, :, :, :] = np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, len(self.ell_bins) + n_mode)),original_shape)
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rBand power covariance calculation for the Gaussian '
                            'ggmm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
                    gauss_BPEggmm_mix = 0
                    gauss_BPBggmm_mix = 0
                    gauss_BPEggmm_sn = 0
                    gauss_BPBggmm_sn = 0
            print("")
        else:
            gauss_BPEggmm_sva, gauss_BPEggmm_mix, gauss_BPEggmm_sn = 0, 0, 0
            gauss_BPBggmm_sva, gauss_BPBggmm_mix, gauss_BPBggmm_sn = 0, 0, 0

        if self.gm:
            gauss_BPgmgm_sva = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_lens, self.n_tomo_clust, self.n_tomo_lens))
            gauss_BPgmgm_mix = np.zeros_like(gauss_BPgmgm_sva)
            gauss_BPgmgm_sn = np.zeros_like(gauss_BPgmgm_sva)
            original_shape = gauss_BPgmgm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**2*self.n_tomo_lens**2
            gaussELL_sva_flat = np.reshape(gaussELLgmgm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLgmgm_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPgmgm_sva[m_mode, n_mode, :, :, :, :, :, :] = 2.*np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_ggl']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode + 2*len(self.ell_bins), n_mode + 2*len(self.ell_bins))),original_shape)
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPgmgm_mix[m_mode, n_mode, :, :, :, :, :, :] = 2.*np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_ggl']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode + 2*len(self.ell_bins), n_mode + 2*len(self.ell_bins))),original_shape)
                    
                    gauss_BPgmgm_sn[n_mode, m_mode, :, :, :, :, :, :] = 4*np.pi**2/self.N_ell[m_mode]/self.N_ell[n_mode]*(kron_delta_tomo_clust[None, None, :, None, :, None]
                                                                            * kron_delta_tomo_lens[None, None, None, :, None, :]) \
                                                                            * survey_params_dict['ellipticity_dispersion'][None, :]**2*self.SN_integral_gmgm[m_mode, n_mode, None, None, :, : ,None, None] 
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rBand power covariance calculation for the Gaussian '
                            'gmgm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            gauss_BPgmgm_sva, gauss_BPgmgm_mix, gauss_BPgmgm_sn = 0, 0, 0


        if self.mm and self.gm and self.cross_terms:
            gauss_BPEmmgm_sva = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_clust, self.n_tomo_lens))
            gauss_BPEmmgm_mix = np.zeros_like(gauss_BPEmmgm_sva)
            gauss_BPBmmgm_sva = np.zeros_like(gauss_BPEmmgm_sva)
            gauss_BPBmmgm_mix = np.zeros_like(gauss_BPEmmgm_sva)
            
            original_shape = gauss_BPEmmgm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust*self.n_tomo_lens**3
            gaussELL_sva_flat = np.reshape(gaussELLmmgm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLmmgm_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPEmmgm_sva[m_mode, n_mode, :, :, :, :, :, :] = np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, 2*len(self.ell_bins) + n_mode)),original_shape)
                    gauss_BPBmmgm_sva[m_mode, n_mode, :, :, :, :, :, :] = np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], len(self.ell_bins) + m_mode, 2*len(self.ell_bins) + n_mode)),original_shape)
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPEmmgm_mix[m_mode, n_mode, :, :, :, :, :, :] = np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, 2*len(self.ell_bins) + n_mode)),original_shape)
                    gauss_BPBmmgm_mix[m_mode, n_mode, :, :, :, :, :, :] = np.pi/self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_clust']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], len(self.ell_bins) + m_mode, 2*len(self.ell_bins) + n_mode)),original_shape)
                    
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rBand power covariance calculation for the Gaussian '
                            'mmgm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
                    gauss_BPEmmgm_sn = 0
                    gauss_BPBmmgm_sn = 0
            print("")
        else:
            gauss_BPEmmgm_sva, gauss_BPEmmgm_mix, gauss_BPEmmgm_sn = 0, 0, 0
            gauss_BPBmmgm_sva, gauss_BPBmmgm_mix, gauss_BPBmmgm_sn = 0, 0, 0

        if self.mm:
            gauss_BPEEmmmm_sva = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_lens))
            gauss_BPEEmmmm_mix = np.zeros_like(gauss_BPEEmmmm_sva)
            gauss_BPEEmmmm_sn = np.zeros_like(gauss_BPEEmmmm_sva)
            gauss_BPBBmmmm_sva = np.zeros_like(gauss_BPEEmmmm_sva)
            gauss_BPBBmmmm_sn = np.zeros_like(gauss_BPEEmmmm_sva)
            gauss_BPBBmmmm_mix = np.zeros_like(gauss_BPEEmmmm_sva)
            gauss_BPEBmmmm_sva = np.zeros_like(gauss_BPEEmmmm_sva)
            gauss_BPEBmmmm_mix = np.zeros_like(gauss_BPEEmmmm_sva)
            
            original_shape = gauss_BPEEmmmm_sva[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**4
            gaussELL_sva_flat = np.reshape(gaussELLmmmm_sva, (len(self.ellrange), len(
                self.ellrange), flat_length))
            gaussELL_mix_flat = np.reshape(gaussELLmmmm_mix, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_sva_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPEEmmmm_sva[m_mode, n_mode, :, :, :, :, :, :] = np.pi/2./self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_lens']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gauss_BPEBmmmm_sva[m_mode, n_mode, :, :, :, :, :, :] = np.pi/2./self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_lens']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode + len(self.ell_bins))),original_shape)
                    gauss_BPBBmmmm_sva[m_mode, n_mode, :, :, :, :, :, :] = np.pi/2./self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_lens']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode + len(self.ell_bins), n_mode + len(self.ell_bins))),original_shape)
                    self.levin_int.init_integral(self.ellrange, np.moveaxis(np.diagonal(gaussELL_mix_flat)*self.ellrange,0,-1), True, True)
                    gauss_BPEEmmmm_mix[m_mode, n_mode, :, :, :, :, :, :] = np.pi/2./self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_lens']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode)),original_shape)
                    gauss_BPEBmmmm_mix[m_mode, n_mode, :, :, :, :, :, :] = np.pi/2./self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_lens']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode, n_mode + len(self.ell_bins))),original_shape)
                    gauss_BPBBmmmm_mix[m_mode, n_mode, :, :, :, :, :, :] = np.pi/2./self.N_ell[m_mode]/self.N_ell[n_mode]/(survey_params_dict['survey_area_lens']/self.deg2torad2) * np.reshape(np.array(self.levin_int.cquad_integrate_double_well(self.ell_limits[m_mode][:], m_mode + len(self.ell_bins), n_mode + len(self.ell_bins))),original_shape)
                    
                    gauss_BPEEmmmm_sn[n_mode, m_mode, :, :, :, :, :, :] = 2*np.pi**2/self.N_ell[m_mode]/self.N_ell[n_mode]*(kron_delta_tomo_lens[None, None, :, None, :, None]
                                                                            * kron_delta_tomo_lens[None, None, None, :, None, :]
                                                                            + kron_delta_tomo_lens[None, None, :, None, None, :]
                                                                            * kron_delta_tomo_lens[None, None, None, :, :, None]) \
                                                                            * (survey_params_dict['ellipticity_dispersion']**2)[None, None, :, None, None, None] \
                                                                            * (survey_params_dict['ellipticity_dispersion']**2)[None, None, None, :, None, None]*self.SN_integral_mmmm[m_mode, n_mode, None, None, :, : ,None, None] 
                    gauss_BPBBmmmm_sn[n_mode, m_mode, :, :, :, :, :, :] = gauss_BPEEmmmm_sn[n_mode, m_mode, :, :, :, :, :, :]
                    eta = (time.time()-t0) / \
                        60 * (tcombs/tcomb-1)
                    print('\rBand power covariance calculation for the Gaussian '
                            'mmmm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            gauss_BPEBmmmm_sn = 0
            print("")
        else:
            gauss_BPEEmmmm_sva, gauss_BPEEmmmm_mix, gauss_BPEEmmmm_sn = 0, 0, 0
            gauss_BPBBmmmm_sva, gauss_BPBBmmmm_mix, gauss_BPBBmmmm_sn = 0, 0, 0
            gauss_BPEBmmmm_sva, gauss_BPEBmmmm_mix, gauss_BPEBmmmm_sn = 0, 0, 0 
        print("\nWrapping up all Gaussian bandpower covariance contributions.")


        return gauss_BPgggg_sva, gauss_BPgggg_mix, gauss_BPgggg_sn, \
            gauss_BPgggm_sva, gauss_BPgggm_mix, gauss_BPgggm_sn, \
            gauss_BPEggmm_sva, gauss_BPEggmm_mix, gauss_BPEggmm_sn, \
            gauss_BPBggmm_sva, gauss_BPBggmm_mix, gauss_BPBggmm_sn, \
            gauss_BPgmgm_sva, gauss_BPgmgm_mix, gauss_BPgmgm_sn, \
            gauss_BPEmmgm_sva, gauss_BPEmmgm_mix, gauss_BPEmmgm_sn, \
            gauss_BPBmmgm_sva, gauss_BPBmmgm_mix, gauss_BPBmmgm_sn, \
            gauss_BPEEmmmm_sva, gauss_BPEEmmmm_mix, gauss_BPEEmmmm_sn, \
            gauss_BPEBmmmm_sva, gauss_BPEBmmmm_mix, gauss_BPEBmmmm_sn, \
            gauss_BPBBmmmm_sva, gauss_BPBBmmmm_mix, gauss_BPBBmmmm_sn


    def covbandpowers_non_gaussian(self,
                                   covELLspacesettings,
                                   survey_params_dict,
                                   output_dict,
                                   bias_dict,
                                   hod_dict,
                                   prec,
                                   tri_tab):
        """
        Calculates the non-Gaussian covariance between all observables for the
        band powers as specified in the config file.

        Parameters
        ----------
        covELLspacesettings : dictionary
            Specifies the exact details of the projection to ell space.
            The projection from wavefactor k to angular scale ell is
            done first, followed by the projection to real space in this
            class
        survey_params_dict : dictionary
            Specifies all the information unique to a specific survey.
            Relevant values are the effective number density of galaxies
            for all tomographic bins as well as the ellipticity
            dispersion for galaxy shapes. To be passed from the
            read_input method of the Input class.
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
        hm_prec : dictionary
            Contains precision information about the HaloModel (also,
            see hmf documentation by Steven Murray), this includes mass
            range and spacing for the mass integrations in the halo
            model.
        tri_tab : dictionary
            Look-up table for the trispectra (for all combinations of
            matter 'm' and tracer 'g', optional).
            Possible keys: '', 'z', 'mmmm', 'mmgm', 'gmgm', 'ggmm',
            'gggm', 'gggg'
        
        Returns
        -------
            nongauss_BPgggg, nongauss_BPgggm, nongauss_BPEggmm, nongauss_BPBggmm, \
            nongauss_BPgmgm, nongauss_BPEmmgm, nongauss_BPBmmgm, nongauss_BPEEmmmm, \
            nongauss_BPEBmmmm, nongauss_BPBBmmmm : list of arrays

            each entry with shape (ell bins, ell bins,
                                   sample bins, sample bins,
                                   no_tomo_clust\lens, no_tomo_clust\lens,
                                   no_tomo_clust\lens, no_tomo_clust\lens)
        
        """

        if not self.cov_dict['nongauss']:
            return 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        else:
            return self.__covbandpowers_4pt_projection(covELLspacesettings,
                                                       survey_params_dict,
                                                       output_dict,
                                                       bias_dict,
                                                       hod_dict,
                                                       prec,
                                                       tri_tab,
                                                       True)
    def covbandpowers_ssc(self,
                          covELLspacesettings,
                          survey_params_dict,
                          output_dict,
                          bias_dict,
                          hod_dict,
                          prec,
                          tri_tab):
        """
        Calculates the super sample covariance between all observables for
        bandpowers as specified in the config file.

        Parameters
        ----------
        covELLspacesettings : dictionary
            Specifies the exact details of the projection to ell space.
            The projection from wavefactor k to angular scale ell is
            done first, followed by the projection to real space in this
            class
        survey_params_dict : dictionary
            Specifies all the information unique to a specific survey.
            Relevant values are the effective number density of galaxies
            for all tomographic bins as well as the ellipticity
            dispersion for galaxy shapes. To be passed from the
            read_input method of the Input class.
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
        hm_prec : dictionary
            Contains precision information about the HaloModel (also,
            see hmf documentation by Steven Murray), this includes mass
            range and spacing for the mass integrations in the halo
            model.
        tri_tab : dictionary
            Look-up table for the trispectra (for all combinations of
            matter 'm' and tracer 'g', optional).
            Possible keys: '', 'z', 'mmmm', 'mmgm', 'gmgm', 'ggmm',
            'gggm', 'gggg'
        
        Returns
        -------
            nongauss_BPgggg, nongauss_BPgggm, nongauss_BPEggmm, nongauss_BPBggmm, \
            nongauss_BPgmgm, nongauss_BPEmmgm, nongauss_BPBmmgm, nongauss_BPEEmmmm, \
            nongauss_BPEBmmmm, nongauss_BPBBmmmm : list of arrays

            each entry with shape (ell bins, ell bins,
                                   sample bins, sample bins,
                                   no_tomo_clust\lens, no_tomo_clust\lens,
                                   no_tomo_clust\lens, no_tomo_clust\lens)
        """

        if not self.cov_dict['ssc']:
            return 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        else:
            return self.__covbandpowers_4pt_projection(covELLspacesettings,
                                                       survey_params_dict,
                                                       output_dict,
                                                       bias_dict,
                                                       hod_dict,
                                                       prec,
                                                       tri_tab,
                                                       False)

    def __covbandpowers_4pt_projection(self,
                                       covELLspacesettings,
                                       survey_params_dict,
                                       output_dict,
                                       bias_dict,
                                       hod_dict,
                                       prec,
                                       tri_tab,
                                       connected):
        """
        Auxillary function to integrate four point functions from ell space to
        bandpower space for all observables specified in the input file.

        Parameters
        ----------
        covELLspacesettings : dictionary
            Specifies the exact details of the projection to ell space.
            The projection from wavefactor k to angular scale ell is
            done first, followed by the projection to real space in this
            class
        survey_params_dict : dictionary
            Specifies all the information unique to a specific survey.
            Relevant values are the effective number density of galaxies
            for all tomographic bins as well as the ellipticity
            dispersion for galaxy shapes. To be passed from the
            read_input method of the Input class.
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
        hm_prec : dictionary
            Contains precision information about the HaloModel (also,
            see hmf documentation by Steven Murray), this includes mass
            range and spacing for the mass integrations in the halo
            model.
        tri_tab : dictionary
            Look-up table for the trispectra (for all combinations of
            matter 'm' and tracer 'g', optional).
            Possible keys: '', 'z', 'mmmm', 'mmgm', 'gmgm', 'ggmm',
            'gggm', 'gggg'
        connected : boolean
            If True the trispectrum is considered
            If False the SSC is considered

        Returns
        -------
            nongauss_CEgggg, nongauss_CEgggm, nongauss_CEggmm, nongauss_CBggmm, \
            nongauss_CEgmgm, nongauss_CEmmgm, nongauss_CBmmgm, nongauss_CEEmmmm, \
            nongauss_CEBmmmm, nongauss_CBBmmmm
        
            each entry with shape (ell bins, ell bins,
                                   sample bins, sample bins,
                                   no_tomo_clust\lens, no_tomo_clust\lens,
                                   no_tomo_clust\lens, no_tomo_clust\lens)
        """

        nongauss_BPgggg = None
        nongauss_BPgggm = None
        nongauss_BPEggmm = None
        nongauss_BPBggmm = None
        nongauss_BPgmgm = None
        nongauss_BPEmmgm = None
        nongauss_BPBmmgm = None
        nongauss_BPEEmmmm = None
        nongauss_BPEBmmmm = None
        nongauss_BPBBmmmm = None
        if (connected):
            nongaussELLgggg, nongaussELLgggm, nongaussELLggmm, nongaussELLgmgm, nongaussELLmmgm, nongaussELLmmmm = self.covELL_non_gaussian(
                covELLspacesettings, output_dict, bias_dict, hod_dict, prec, tri_tab)
        else:
            nongaussELLgggg, nongaussELLgggm, nongaussELLggmm, nongaussELLgmgm, nongaussELLmmgm, nongaussELLmmmm = self.covELL_ssc(
                bias_dict, hod_dict, prec, survey_params_dict, covELLspacesettings)
        if self.gg:
            nongauss_BPgggg = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust))
            original_shape = nongauss_BPgggg[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**4
            nongaussELL_flat = np.reshape(nongaussELLgggg, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongauss_BPgggg[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    if connected:
                        nongauss_BPgggg[m_mode, n_mode, :, :, :, :, :, :] /= (survey_params_dict['survey_area_clust'] / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rBandpower E-mode covariance calculation for the '
                            'nonGaussian gggg term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            nongauss_BPgggg = 0

        if self.gg and self.gm and self.cross_terms:
            nongauss_BPgggm = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_lens))
            original_shape = nongauss_BPgggm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**3*self.n_tomo_lens
            nongaussELL_flat = np.reshape(nongaussELLgggm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode + 2*len(self.ell_bins)][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongauss_BPgggm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    if connected:
                        nongauss_BPgggm[m_mode, n_mode, :, :, :, :, :, :] /= (max(survey_params_dict['survey_area_clust'],survey_params_dict['survey_area_ggl']) / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rBandpower E-mode covariance calculation for the '
                            'nonGaussian gggm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            nongauss_BPgggm = 0

        if self.gg and self.mm and self.cross_terms:
            nongauss_BPEggmm = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_lens, self.n_tomo_lens))
            nongauss_BPBggmm = np.zeros_like(nongauss_BPEggmm)
            original_shape = nongauss_BPEggmm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**2*self.n_tomo_lens**2
            nongaussELL_flat = np.reshape(nongaussELLggmm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    inner_integralE = np.zeros((len(self.ellrange), flat_length))
                    inner_integralB = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integralE[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                        inner_integralB[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode + len(self.ell_bins)][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integralE*self.ellrange[:, None], True, True)
                    nongauss_BPEggmm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    self.levin_int.init_integral(self.ellrange, inner_integralB*self.ellrange[:, None], True, True)
                    nongauss_BPBggmm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    if connected:
                        nongauss_BPEggmm[m_mode, n_mode, :, :, :, :, :, :] /= (2.*max(survey_params_dict['survey_area_clust'],survey_params_dict['survey_area_lens']) / self.deg2torad2)
                        nongauss_BPBggmm[m_mode, n_mode, :, :, :, :, :, :] /= (2.*max(survey_params_dict['survey_area_clust'],survey_params_dict['survey_area_lens']) / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rBandpower E-mode covariance calculation for the '
                            'nonGaussian ggmm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            nongauss_BPEggmm = 0
            nongauss_BPBggmm = 0

        if self.gm:
            nongauss_BPgmgm = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_clust, self.n_tomo_lens))
            original_shape = nongauss_BPgmgm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust**2*self.n_tomo_lens**2
            nongaussELL_flat = np.reshape(nongaussELLgmgm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode + 2*len(self.ell_bins)][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongauss_BPgmgm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode +  2*len(self.ell_bins)][:], m_mode)),original_shape)
                    if connected:
                        nongauss_BPgmgm[m_mode, n_mode, :, :, :, :, :, :] /= (survey_params_dict['survey_area_ggl']) / self.deg2torad2
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rBandpower E-mode covariance calculation for the '
                            'nonGaussian gmgm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            nongauss_BPgmgm = 0


        if self.mm and self.gm and self.cross_terms:
            nongauss_BPEmmgm = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_clust, self.n_tomo_lens))
            nongauss_BPBmmgm = np.zeros_like(nongauss_BPEmmgm)
            original_shape = nongauss_BPEmmgm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_clust*self.n_tomo_lens**3
            nongaussELL_flat = np.reshape(nongaussELLmmgm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    inner_integral = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integral[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode + 2*len(self.ell_bins)][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integral*self.ellrange[:, None], True, True)
                    nongauss_BPEmmgm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    nongauss_BPBmmgm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode + len(self.ell_bins)][:], m_mode)),original_shape)
                    if connected:
                        nongauss_BPEmmgm[m_mode, n_mode, :, :, :, :, :, :] /= (2.*max(survey_params_dict['survey_area_ggl'],survey_params_dict['survey_area_lens']) / self.deg2torad2)
                        nongauss_BPBmmgm[m_mode, n_mode, :, :, :, :, :, :] /= (2.*max(survey_params_dict['survey_area_ggl'],survey_params_dict['survey_area_lens']) / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rBandpower E-mode covariance calculation for the '
                            'nonGaussian mmgm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
        else:
            nongauss_BPEmmgm, nongauss_BPBmmgm = 0, 0

        if self.mm:
            nongauss_BPEEmmmm = np.zeros(
                (len(self.ell_bins), len(self.ell_bins), self.sample_dim, self.sample_dim, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_lens, self.n_tomo_lens))
            nongauss_BPEBmmmm = np.zeros_like(nongauss_BPEEmmmm)
            nongauss_BPBBmmmm = np.zeros_like(nongauss_BPEEmmmm)
            original_shape = nongauss_BPEEmmmm[0, 0, :, :, :, :, :, :].shape
            flat_length = self.sample_dim*self.sample_dim*self.n_tomo_lens**4
            nongaussELL_flat = np.reshape(nongaussELLmmmm, (len(self.ellrange), len(
                self.ellrange), flat_length))
            t0, tcomb = time.time(), 1
            tcombs = len(self.ell_bins)**2
            for m_mode in range(len(self.ell_bins)):
                for n_mode in range(len(self.ell_bins)):
                    inner_integralE = np.zeros((len(self.ellrange), flat_length))
                    inner_integralB = np.zeros((len(self.ellrange), flat_length))
                    for i_ell in range(len(self.ellrange)):
                        self.levin_int.init_integral(self.ellrange, nongaussELL_flat[:, i_ell, :]*self.ellrange[:, None], True, True)
                        inner_integralE[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode][:], n_mode))
                        inner_integralB[i_ell, :] = np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[n_mode + len(self.ell_bins)][:], n_mode))
                    self.levin_int.init_integral(self.ellrange, inner_integralE*self.ellrange[:, None], True, True)
                    nongauss_BPEEmmmm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode][:], m_mode)),original_shape)
                    nongauss_BPEBmmmm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode + len(self.ell_bins)][:], m_mode)),original_shape)
                    self.levin_int.init_integral(self.ellrange, inner_integralB*self.ellrange[:, None], True, True)
                    nongauss_BPBBmmmm[m_mode, n_mode, :, :, :, :, :, :] = 1.0/(self.N_ell[m_mode]*self.N_ell[n_mode])*np.reshape(np.array(self.levin_int.cquad_integrate_single_well(self.ell_limits[m_mode + len(self.ell_bins)][:], m_mode)),original_shape)
                    if connected:
                        nongauss_BPEEmmmm[m_mode, n_mode, :, :, :, :, :, :] /= (4.*survey_params_dict['survey_area_lens'] / self.deg2torad2)
                        nongauss_BPEBmmmm[m_mode, n_mode, :, :, :, :, :, :] /= (4.*survey_params_dict['survey_area_lens'] / self.deg2torad2)
                        nongauss_BPBBmmmm[m_mode, n_mode, :, :, :, :, :, :] /= (4.*survey_params_dict['survey_area_lens'] / self.deg2torad2)
                    eta = (time.time()-t0) / \
                            60 * (tcombs/tcomb-1)
                    print('\rBandpower E-mode covariance calculation for the '
                            'nonGaussian mmmm term '
                            + str(round(tcomb/tcombs*100, 1)) + '% in '
                            + str(round(((time.time()-t0)/60), 1)) +
                            'min  ETA '
                            'in ' + str(round(eta, 1)) + 'min', end="")
                    tcomb += 1
            print("")
            
        else:
            nongauss_BPEEmmmm, nongauss_BPBBmmmm, nongauss_BPEBmmmm = 0, 0, 0

        return nongauss_BPgggg, nongauss_BPgggm, nongauss_BPEggmm, nongauss_BPBggmm, \
            nongauss_BPgmgm, nongauss_BPEmmgm, nongauss_BPBmmgm, nongauss_BPEEmmmm, \
            nongauss_BPEBmmmm, nongauss_BPBBmmmm


