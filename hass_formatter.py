def hass_format_config(discovery,object_id,node_name,state_topic,command_topic,session):
    features=[]
    if discovery.can_update:
        features.append('INSTALL')
    if discovery.release_url:
        features.append('RELEASE_NOTES')
    config= {
        'name':'%s %s on %s' % (discovery.name,discovery.source_type, node_name),
        'device_class':None, # not firmware, so defaults to null
        'unique_id':object_id,
        'state_topic':state_topic,
        'command_topic':command_topic,
        'payload_install':'{"source_type":"%s","name":"%s","command":"install"}' % (discovery.source_type,discovery.name),
        'source_session':session,
        'supported_features':features,
        'entity_picture'    : discovery.entity_picture_url,
        'icon'              : discovery.device_icon,
        'latest_version_topic':state_topic,
        'latest_version_template':'{{value_json.latest_version}}',
    } 
    config.update(discovery.provider.hass_config_format(discovery))
    return config
    
def hass_format_state(discovery,node_name,session):
    state= {
        'state'             : discovery.status,
        'installed_version' : discovery.current_version,
        'latest_version'    : discovery.latest_version,
        'title'             : discovery.title_template.format(name=discovery.name,node=node_name),
        'release_url'       : discovery.release_url,
        'release_summary'   : discovery.release_summary,
        'source_session'    : session
    } 
    state.update(discovery.provider.hass_state_format(discovery))
    return state
