#!/usr/bin/env python3
"""Tests for browser surface readiness validation."""

from __future__ import annotations

import unittest

from validate_browser_surface_readiness import validate_surface


class BrowserSurfaceReadinessTests(unittest.TestCase):
    def test_chrome_sign_in_blocks(self) -> None:
        result = validate_surface(
            {
                "browser": "chrome",
                "mode": "mutation_preparation",
                "targetAction": "save_design",
                "siteKey": "abc123",
                "currentUrl": "https://workspace.laicms.com/sign-in",
            }
        )

        self.assertEqual(result["status"], "blocked_login_required")
        self.assertIn("browser is on workspace sign-in page", result["issues"])
        self.assertFalse(result["remoteMutationAuthorized"])

    def test_in_app_zero_width_designer_blocks_mutation(self) -> None:
        result = validate_surface(
            {
                "browser": "in_app",
                "mode": "mutation_preparation",
                "targetAction": "save_design",
                "siteKey": "abc123",
                "currentUrl": "https://workspace.laicms.com/abc123/themes/theme/page/design",
                "designerVisible": True,
                "previewFrameWidth": 0,
                "previewFrameHeight": 640,
                "canvasText": "Render canvas...",
                "saveEnabled": False,
            }
        )

        self.assertEqual(result["status"], "blocked_browser_surface")
        self.assertIn("preview frame has zero width or height", result["issues"])
        self.assertIn("designer canvas is still stuck on Render canvas", result["issues"])
        self.assertIn("save control is disabled for requested design mutation", result["issues"])

    def test_valid_designer_surface_passes_mutation_preparation(self) -> None:
        result = validate_surface(
            {
                "browser": "chrome",
                "mode": "mutation_preparation",
                "targetAction": "save_design",
                "siteKey": "abc123",
                "currentUrl": "https://workspace.laicms.com/abc123/themes/theme/page/design",
                "designerVisible": True,
                "previewFrameWidth": 1200,
                "previewFrameHeight": 720,
                "canvasText": "Home page canvas",
                "saveEnabled": True,
            }
        )

        self.assertEqual(result["status"], "ready_for_mutation_preparation")
        self.assertEqual(result["issues"], [])
        self.assertIn("preview_frame_nonzero", result["proven"])

    def test_readonly_can_report_limited_designer_surface(self) -> None:
        result = validate_surface(
            {
                "browser": "in_app",
                "mode": "readonly",
                "targetAction": "save_design",
                "siteKey": "abc123",
                "currentUrl": "https://workspace.laicms.com/abc123/themes/theme/page/design",
                "designerVisible": True,
                "previewFrameWidth": 0,
                "previewFrameHeight": 720,
                "canvasText": "Render canvas...",
            }
        )

        self.assertEqual(result["status"], "ready_for_readonly")
        self.assertIn("preview frame has zero width or height", result["issues"])
        self.assertFalse(result["remoteMutationAuthorized"])


if __name__ == "__main__":
    unittest.main()
