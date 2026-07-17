import pytest
from unittest.mock import patch, MagicMock
import sys
import argparse
import pathlib

from singularity.cli import main, generate_docs, setup_logging

def test_setup_logging():
    with patch('logging.basicConfig') as mock_basic:
        setup_logging(True)
        mock_basic.assert_called_once()
        setup_logging(False)
        assert mock_basic.call_count == 2

def test_generate_docs(tmp_path):
    with patch('pathlib.Path.cwd', return_value=tmp_path):
        docs_path = generate_docs()
        assert (tmp_path / "docs.html").exists()
        assert "Simulated Singularity CC Documentation" in pathlib.Path(docs_path).read_text(encoding="utf-8")

@patch('singularity.cli.generate_docs', return_value="fake/path")
@patch('webbrowser.open')
def test_main_help(mock_open, mock_generate):
    test_args = ["singularity", "-h"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
        mock_generate.assert_called_once()
        mock_open.assert_called_once()

@patch('subprocess.run')
def test_main_test_coverage_100(mock_run):
    test_args = ["singularity", "-t"]
    mock_run.return_value.stdout = "100%"
    mock_run.return_value.stderr = ""
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
        mock_run.assert_called_once()

@patch('subprocess.run')
def test_main_test_coverage_incomplete(mock_run):
    test_args = ["singularity", "-t"]
    mock_run.return_value.stdout = "95%"
    mock_run.return_value.stderr = "some error"
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
        mock_run.assert_called_once()

@patch('subprocess.run')
def test_main_interactive(mock_run):
    test_args = ["singularity", "-i"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
        mock_run.assert_called_once()

@patch('singularity.cli.run_autonomous')
def test_main_autonomous(mock_run):
    test_args = ["singularity", "-a"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
        mock_run.assert_called_once()

@patch('singularity.cli.run_autonomous')
def test_main_sandbox(mock_run_auto):
    test_args = ["singularity", "-s"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
        import os
        assert os.environ.get("SINGULARITY_DB_PATH") == ":memory:"
        mock_run_auto.assert_called_once()

@patch('argparse.ArgumentParser.print_help')
def test_main_default(mock_print_help):
    test_args = ["singularity"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
        mock_print_help.assert_called_once()

def test_run_autonomous_interrupt():
    from singularity.cli import run_autonomous
    with patch('singularity.core.agent_registry.initialize_constellation'), \
         patch('singularity.orchestration.graph.build_graph'):
        # Mock the while loop to raise KeyboardInterrupt
        with patch('singularity.cli.True', False):
            pass
