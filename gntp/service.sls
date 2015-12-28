salt-growl:
  service.running:
    - enable: True
  file.managed:
    - name: /lib/systemd/system/salt-growl.service
    - source: salt://gntp/files/lib/systemd/system/salt-growl.service
    - require_in:
      - service: salt-growl
