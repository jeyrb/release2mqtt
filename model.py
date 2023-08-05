 
class Discovery:
    ''' Discovered component from a scan '''
    def __init__(self,source_type,name,entity_picture_url=None,
                 restarter=None, fetcher=None,rescanner=None,
                 current_version=None,latest_version=None,
                 release_url=None,release_summary=None,title_template=None,
                 device_icon=None,custom=None):
        self.source_type=source_type
        self.name=name
        self.entity_picture_url=entity_picture_url
        self.current_version=current_version
        self.latest_version=latest_version
        self.restarter=restarter
        self.fetcher=fetcher
        self.rescanner=rescanner
        self.release_url=release_url
        self.release_summary=release_summary
        self.title_template=title_template
        self.device_icon=device_icon
        self.custom=custom or {}
        
class Fetcher:
    def fetch(self):
        pass

class Restarter:
    def restart(self):
        pass