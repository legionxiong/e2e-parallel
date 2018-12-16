import os
import subprocess

def run_test(path_str, setup_log=None):
    if setup_log:
        log_path = setup_log
    else:
        log_path = os.path.join(os.getenv('LOGDIR'), 'running_log.txt')
    log_dir = os.path.dirname(log_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    path_list = [p.strip() for p in path_str.split(',')]
    for test in path_list:
        cmd = 'npm run dev-e2e -- test/e2e/specs/%s.js' % test
        with open(log_path, 'a+') as logfl:
            cslst = os.getenv('CASELIST')
            if cslst == 'true':
                process = subprocess.Popen(cmd, shell=True, cwd='mevoco-ui2')
            else:
                process = subprocess.Popen(cmd, shell=True, stdout=logfl, stderr=logfl, cwd='mevoco-ui2')
            process.communicate()
        if process.returncode != 0:
            if cslst != 'true':
                with open(log_path, 'rt') as logfl:
                    log = logfl.readlines()
                for line in log:
                    if 'Error' in line:
                        err_index = log.index(line)
                for output in log[err_index - 5 : err_index + 5]:
                    print output
            raise AssertionError()