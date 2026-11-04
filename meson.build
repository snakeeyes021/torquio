# Torquio's GUI (gui/, docs/GUI.md). The command-line Torquio doesn't use Meson; this is only for building the
# GUI, from GNOME Builder or with flatpak-builder (tech.redfoxlabs.Torquio.json).
project('torquio-gui',
          version: '0.7.0',
    meson_version: '>= 1.0.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

i18n = import('i18n')
gnome = import('gnome')

application_id = 'tech.redfoxlabs.Torquio'

subdir('gui')

gnome.post_install(
     glib_compile_schemas: true,
    gtk_update_icon_cache: true,
  update_desktop_database: true,
)
