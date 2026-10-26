"""Shared membership products. Internal customer role remains player/host."""
PLANS = {
    'player': dict(name='Player', price='29.00', role='player', table_limit=0),
    'host_starter': dict(name='Host Starter', price='299.00', role='host', table_limit=6, tier='starter'),
    'host_pro': dict(name='Host Pro', price='599.00', role='host', table_limit=20, tier='pro'),
}

def product_key(value):
    value = str(value or '').lower()
    return 'host_pro' if value == 'host' else value

def product(value):
    return PLANS[product_key(value)]

def host_tier(user):
    return 'starter' if (user or {}).get('host_tier') == 'starter' else 'pro'

def host_product(user):
    return 'host_' + host_tier(user)

def table_limit(user):
    return PLANS[host_product(user)]['table_limit']

def host_name(user):
    return PLANS[host_product(user)]['name']
