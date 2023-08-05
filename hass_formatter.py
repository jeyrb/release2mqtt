def hass_format_config(discovery,object_id,node_name,state_topic,command_topic):
    return {
        'name':'%s %s' % (discovery.name,discovery.source_type),
        'device_class':None, # not firmware, so defaults to null
        'unique_id':object_id,
        'state_topic':state_topic,
        'command_topic':command_topic,
        'payload_install':'install',
        'latest_version_topic':state_topic,
        'latest_version_template':'{{value_json.latest_version}}',
    }  
    
def hass_state_config(discovery,node_name):
    return {
        'state'             : 'on' if discovery.latest_version != discovery.current_version else 'off',
        'installed_version' : discovery.current_version,
        'latest_version'    : discovery.latest_version,
        'title'             : discovery.title_template.format(name=discovery.name,node=node_name),
        'release_url'       : discovery.release_url,
        'release_summary'   : discovery.release_summary,
        'entity_picture'    : discovery.entity_picture_url,
        'icon'              : discovery.device_icon
    } 