#!/usr/bin/env python3
"""
Quick CLI test script - tests core functionality
"""

import subprocess
import sys

def test_command(command, description):
    """Test a single CLI command"""
    try:
        result = subprocess.run(
            f"docker-compose exec playlist-app playlist {command}".split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✓ {description}")
            return True
        else:
            print(f"✗ {description} (exit code: {result.returncode})")
            if result.stderr:
                print(f"  Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ {description} (timeout)")
        return False
    except Exception as e:
        print(f"✗ {description} (exception: {e})")
        return False

def main():
    """Run quick CLI tests"""
    print("Quick CLI Test Suite")
    print("=" * 40)
    
    tests = [
        ("health", "Health check"),
        ("status", "System status"),
        ("discovery stats", "Discovery statistics"),
        ("discovery list --limit 5", "Discovery list"),
        ("discovery status", "Discovery status"),
        ("analysis stats", "Analysis statistics"),
        ("analysis categorize", "Analysis categorize"),
        ("analysis status", "Analysis status"),
        ("config list", "Config list"),
        ("config show discovery", "Config show discovery"),
        ("config validate", "Config validate"),
        ("config reload", "Config reload"),
        ("metadata stats", "Metadata statistics"),
        ("metadata search --query test --limit 5", "Metadata search"),
        ("tracks list --limit 10", "Tracks list"),
        ("database status", "Database status"),
        ("--help", "Help command"),
        ("discovery --help", "Discovery help"),
        ("analysis --help", "Analysis help"),
        ("faiss --help", "FAISS help"),
    ]
    
    passed = 0
    failed = 0
    
    for command, description in tests:
        if test_command(command, description):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    print(f"Success Rate: {(passed/(passed+failed))*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All CLI commands are working correctly!")
    else:
        print(f"\n⚠️  {failed} commands need attention")

if __name__ == "__main__":
    main()
