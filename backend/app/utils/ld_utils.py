def get_flag(ld_client, context, flag_key, default_value=False):
    """
    Get a feature flag value from LaunchDarkly.
    If ld_client is None, return default_value.
    """
    if ld_client is None:
        return default_value
    try:
        return ld_client.variation(flag_key, context, default_value)
    except Exception:
        return default_value