pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'torquio_gui'
gnome = import('gnome')

gnome.compile_resources('torquio-gui',
  'torquio-gui.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('APPLICATION_ID', application_id)
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'torquio-gui.in',
  output: 'torquio-gui',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

sources = [
  '__init__.py',
  'host.py',
  'main.py',
  'window.py',
]

install_data(sources, install_dir: moduledir)
