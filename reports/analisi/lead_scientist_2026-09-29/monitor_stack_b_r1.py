"""Bounded read-only monitor for the explicitly authorized private Stack B run."""
import monitor_lead_remote_r1 as frozen_monitor

frozen_monitor.KERNELS = {'stack_b': 'davidmaisterx/vcc-stack-variant-b-r1'}

if __name__ == '__main__':
    frozen_monitor.main()
