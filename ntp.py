from fabric.api import run, sudo, task


@task
def status():
    """Report the VM's NTP status."""
    run("ntpq -p")
    run("/usr/lib/nagios/plugins/check_ntp_time -q -H ntp.ubuntu.com -w 2 -c 3", warn_only=True)


@task
def resync():
    """Forcibly resynchronise the VM's NTP clock.

    If a VM's clock manages to get sufficiently out of sync, ntp will give up,
    forcing a manual intervention.
    """
    sudo("service ntp stop")
    sudo("ntpdate -B ntp.ubuntu.com")
    sudo("service ntp start")
