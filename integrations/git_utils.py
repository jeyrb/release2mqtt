import logging as log
import subprocess
import datetime

def git_trust(repo_path: str):  
    try:
        subprocess.run("git config --global --add safe.directory %s" % repo_path,shell=True,cwd=repo_path)
    except Exception as e:
        log.warn('GIT Unable to trust repo at %s: %s',repo_path,e)
   

def git_timestamp(repo_path: str):
    result=None
    try:
        result=subprocess.run("git log -1 --format=%cI --no-show-signature",
                            cwd=repo_path,
                            shell=True,
                            text=True,
                            capture_output=True)
        return datetime.datetime.fromisoformat(result.stdout.strip())
    except Exception as e:
        log.warn('GIT Unable to parse timestamp at %s - %s: %s',repo_path, result.stdout if result else '<NO RESULT>',e)
    

def git_check_update_available(repo_path:str, timeout: int=120):
    result=None
    try:
        result = subprocess.run(
            "git status -uno",
            capture_output=True,
            text=True,
            shell=True,
            cwd=repo_path,
            timeout=timeout,
        )
        if result.returncode == 0 and "Your branch is behind" in result.stdout:
            return True
    except Exception as e:
        log.warn('GIT Unable to check status %s: %s',result.stdout if result else '<NO RESULT>',e)
 
    
def git_pull(repo_path:str):
    log.info("GIT Pulling git at %s",repo_path)
    proc = subprocess.run(
        "git pull", shell=True, cwd=repo_path, timeout=300
    )
    if proc.returncode == 0:
        log.info("GIT pull at %s successful", repo_path)
        return True
    else:
        log.warn("GIT pull at %s failed: %s",repo_path,proc.returncode)
        return False