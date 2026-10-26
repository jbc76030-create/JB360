"""Comprueba que los botones de la interfaz apunten a funciones e insumos reales."""
import re
import subprocess
from pathlib import Path


def test_every_button_action_and_input_is_wired():
    root = Path(__file__).parent
    html = (root / 'panel.html').read_text()
    script = (root / 'panel.js').read_text()
    assert '<script src="/app.js" defer></script>' in html
    assert not re.search(r'\bon(?:click|change|submit)=', html)
    actions = re.findall(r'<button\b[^>]*data-action="([A-Za-z]+)"', html)
    assert len(actions) >= 30
    registry = re.search(r'const ACTIONS=\{([^}]+)\};', script).group(1)
    registered = {part.split(':')[0] for part in registry.split(',')}
    assert set(actions) <= registered
    referenced = set(re.findall(r"\$\('([^']+)'\)", script)) | set(re.findall(r"v\('([^']+)'\)", script))
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    assert referenced <= ids, sorted(referenced - ids)
    assert len(ids) == len(re.findall(r'\bid="([^"]+)"', html)), 'ID HTML repetido'
    subprocess.run(['node', '--check', str(root / 'panel.js')], check=True, capture_output=True)
