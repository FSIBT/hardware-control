Future Development
==================

Plans for the future include (but are not limited to):
- Adding more instrument drivers
- Expanding the instrument drivers we have to implement more parameters/commands
- Modifying the auto-update functionality of the main app to be more flexible, e.g. custom timeout for each instrument
- Looking into using binary ZMQ messages and sending for example numpy arrays over ZMQ instead of strings
- Create a custom widget that shows all logging messages and lets you filter them on the fly (by loglevel and instrument driver, etc.)
- Code improvement:
   - adding more type hints
   - adding more tests (e.g. figuring out how to test Qt apps)
   - improving the code base (running linters such as pylint)
   - update to Qt6
   - replace some logging instances with raising an exception where appropiate (currently we only use logger.error)
