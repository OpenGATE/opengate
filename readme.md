

# Error handling

Use '''raise_except''' to fail with an exception and trace. 

Helpers functions: '''fatal''', '''warning'''.


# Log management 

In module use: 

'''
    log = logging.getLogger(__name__)
'''

In main: TODO

'''
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
'''


# Units value

