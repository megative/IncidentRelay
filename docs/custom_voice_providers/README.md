# IncidentRelay Custom Voice Providers

Put custom voice provider modules into this directory.

Example:

```text
/usr/local/lib/incidentrelay/voice_providers/my_provider.py
```

The provider name in channel config is the file name without `.py`:

```json
{
  "provider": "my_provider"
}
```

Provider files are executable Python code.

This directory must be writable only by server administrators.

## Full documentation

Repository documentation:

```text
docs/voice-providers/
```

Installed package documentation:

```text
/usr/share/doc/incidentrelay/voice-providers/
```

Example providers:

```text
/usr/share/incidentrelay/examples/voice_providers/
```

After adding or changing a provider, restart IncidentRelay.

```bash
sudo systemctl restart incidentrelay
```
