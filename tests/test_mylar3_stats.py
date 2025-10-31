"""
Tests for Mylar3 statistics modules.

Creates temporary directory structures simulating Mylar3 collections.
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
import pytest

from comic_file_organizer.mylar3_scanner import Mylar3Scanner, SeriesInfo
from comic_file_organizer.mylar3_stats import calculate_statistics


class TestMylar3Scanner:
    """Tests for Mylar3Scanner"""
    
    @pytest.fixture
    def temp_collection(self):
        """Create a temporary collection directory"""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir)
    
    def create_publisher(self, base_dir, name):
        """Helper to create a publisher directory"""
        pub_dir = os.path.join(base_dir, name)
        os.makedirs(pub_dir, exist_ok=True)
        return pub_dir
    
    def create_series(self, pub_dir, name, year, total_issues, status="Ended", comicid=None):
        """Helper to create a series directory with series.json"""
        series_dir = os.path.join(pub_dir, f"{name} ({year})")
        os.makedirs(series_dir, exist_ok=True)
        
        # Create series.json
        series_data = {
            "version": "1.0.2",
            "metadata": {
                "type": "comicSeries",
                "publisher": os.path.basename(pub_dir),
                "name": name,
                "year": year,
                "total_issues": total_issues,
                "status": status,
                "comicid": comicid or 12345
            }
        }
        
        with open(os.path.join(series_dir, "series.json"), "w") as f:
            json.dump(series_data, f)
        
        return series_dir
    
    def create_issue(self, series_dir, issue_num, month="January", year=2025):
        """Helper to create a comic file"""
        series_name = os.path.basename(series_dir).split(" (")[0]
        filename = f"{series_name} #{issue_num:03d} ({month} {year}).cbz"
        filepath = os.path.join(series_dir, filename)
        
        # Create empty file
        Path(filepath).touch()
        return filepath
    
    def test_empty_collection(self, temp_collection):
        """Test scanning an empty collection"""
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        
        assert results.total_publishers == 0
        assert results.total_series == 0
        assert results.total_issues_owned == 0
    
    def test_publisher_with_no_series(self, temp_collection):
        """Test that publishers with no series are ignored"""
        # Create publisher with no series subdirectories
        pub_dir = self.create_publisher(temp_collection, "Empty Publisher")
        # Just add a file (should be ignored)
        Path(os.path.join(pub_dir, "readme.txt")).touch()
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        
        assert results.total_publishers == 0
        assert results.total_series == 0
    
    def test_series_followed_only(self, temp_collection):
        """Test series with no issues (followed only)"""
        pub_dir = self.create_publisher(temp_collection, "Marvel")
        self.create_series(pub_dir, "Spider-Man", 2025, 12)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        
        assert results.total_publishers == 1
        assert results.total_series == 1
        assert results.series_followed_only == 1
        assert results.series_with_issues == 0
        assert results.total_issues_owned == 0
    
    def test_series_with_issues(self, temp_collection):
        """Test series with some issues"""
        pub_dir = self.create_publisher(temp_collection, "Marvel")
        series_dir = self.create_series(pub_dir, "Spider-Man", 2025, 12)
        
        # Add 3 issues
        self.create_issue(series_dir, 1)
        self.create_issue(series_dir, 2)
        self.create_issue(series_dir, 3)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        
        assert results.total_publishers == 1
        assert results.total_series == 1
        assert results.series_with_issues == 1
        assert results.series_followed_only == 0
        assert results.total_issues_owned == 3
        assert results.total_missing_issues == 9  # 12 - 3
    
    def test_complete_series(self, temp_collection):
        """Test complete series (all issues owned)"""
        pub_dir = self.create_publisher(temp_collection, "DC Comics")
        series_dir = self.create_series(pub_dir, "Batman", 2020, 5)
        
        # Add all 5 issues
        for i in range(1, 6):
            self.create_issue(series_dir, i)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        
        assert results.total_series == 1
        assert results.complete_series_count == 1
        assert results.total_issues_owned == 5
        assert results.total_missing_issues == 0
        
        series = results.series[0]
        assert series.is_complete
        assert series.completion_percentage == 100.0
    
    def test_multiple_publishers(self, temp_collection):
        """Test collection with multiple publishers"""
        # Marvel with 2 series
        marvel_dir = self.create_publisher(temp_collection, "Marvel")
        series1 = self.create_series(marvel_dir, "Spider-Man", 2025, 10)
        self.create_issue(series1, 1)
        self.create_series(marvel_dir, "X-Men", 2024, 20)  # followed only
        
        # DC with 1 series
        dc_dir = self.create_publisher(temp_collection, "DC Comics")
        series2 = self.create_series(dc_dir, "Batman", 2023, 15)
        self.create_issue(series2, 1)
        self.create_issue(series2, 2)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        
        assert results.total_publishers == 2
        assert "Marvel" in results.publishers
        assert "DC Comics" in results.publishers
        assert results.total_series == 3
        assert results.series_with_issues == 2
        assert results.series_followed_only == 1
        assert results.total_issues_owned == 3  # 1 + 2
    
    def test_series_without_json(self, temp_collection):
        """Test that series without series.json are skipped"""
        pub_dir = self.create_publisher(temp_collection, "Marvel")
        
        # Create series dir without series.json
        bad_series = os.path.join(pub_dir, "Invalid Series (2020)")
        os.makedirs(bad_series)
        self.create_issue(bad_series, 1)  # Has a file but no metadata
        
        # Create valid series
        good_series = self.create_series(pub_dir, "Spider-Man", 2025, 10)
        self.create_issue(good_series, 1)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        
        # Should only find the valid series
        assert results.total_series == 1
        assert results.series[0].series_name == "Spider-Man"
    
    def test_cbr_files_counted(self, temp_collection):
        """Test that both .cbr and .cbz files are counted"""
        pub_dir = self.create_publisher(temp_collection, "Marvel")
        series_dir = self.create_series(pub_dir, "Spider-Man", 2025, 10)
        
        # Create .cbz file
        Path(os.path.join(series_dir, "Spider-Man #001 (Jan 2025).cbz")).touch()
        
        # Create .cbr file
        Path(os.path.join(series_dir, "Spider-Man #002 (Feb 2025).cbr")).touch()
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        
        assert results.total_issues_owned == 2


class TestMylar3Statistics:
    """Tests for statistical calculations"""
    
    @pytest.fixture
    def temp_collection(self):
        """Create a temporary collection directory"""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir)
    
    def create_test_collection(self, base_dir):
        """Create a complex test collection"""
        # Marvel publisher
        marvel = os.path.join(base_dir, "Marvel")
        os.makedirs(marvel)
        
        # Complete series
        complete = os.path.join(marvel, "Complete Series (2020)")
        os.makedirs(complete)
        self.create_series_json(complete, "Complete Series", 2020, 5)
        for i in range(1, 6):
            Path(os.path.join(complete, f"issue{i}.cbz")).touch()
        
        # Incomplete series
        incomplete = os.path.join(marvel, "Incomplete Series (2021)")
        os.makedirs(incomplete)
        self.create_series_json(incomplete, "Incomplete Series", 2021, 10)
        for i in range(1, 4):
            Path(os.path.join(incomplete, f"issue{i}.cbz")).touch()
        
        # Followed only
        followed = os.path.join(marvel, "Followed Only (2022)")
        os.makedirs(followed)
        self.create_series_json(followed, "Followed Only", 2022, 20)
        
        # DC publisher
        dc = os.path.join(base_dir, "DC Comics")
        os.makedirs(dc)
        
        # Another series
        series = os.path.join(dc, "DC Series (2023)")
        os.makedirs(series)
        self.create_series_json(series, "DC Series", 2023, 8)
        for i in range(1, 7):
            Path(os.path.join(series, f"issue{i}.cbz")).touch()
    
    def create_series_json(self, series_dir, name, year, total_issues):
        """Helper to create series.json"""
        publisher = os.path.basename(os.path.dirname(series_dir))
        data = {
            "version": "1.0.2",
            "metadata": {
                "publisher": publisher,
                "name": name,
                "year": year,
                "total_issues": total_issues,
                "status": "Ended"
            }
        }
        with open(os.path.join(series_dir, "series.json"), "w") as f:
            json.dump(data, f)
    
    def test_publisher_statistics(self, temp_collection):
        """Test per-publisher statistics"""
        self.create_test_collection(temp_collection)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        stats = calculate_statistics(results)
        
        # Check overall stats
        assert stats.total_publishers == 2
        assert stats.total_series == 4
        assert stats.series_with_issues == 3
        assert stats.series_followed_only == 1
        assert stats.complete_series == 1
        
        # Check Marvel stats
        marvel_stats = stats.publishers["Marvel"]
        assert marvel_stats.total_series == 3
        assert marvel_stats.series_with_issues == 2
        assert marvel_stats.complete_series == 1
        assert marvel_stats.total_issues_owned == 8  # 5 + 3
        # Missing = (Complete: 0) + (Incomplete: 7) + (Followed-only: 20) = 27
        assert marvel_stats.total_missing_issues == 27
        
        # Check DC stats
        dc_stats = stats.publishers["DC Comics"]
        assert dc_stats.total_series == 1
        assert dc_stats.series_with_issues == 1
        assert dc_stats.complete_series == 0
        assert dc_stats.total_issues_owned == 6
        assert dc_stats.total_missing_issues == 2
    
    def test_completion_percentage(self, temp_collection):
        """Test overall completion percentage calculation"""
        self.create_test_collection(temp_collection)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        stats = calculate_statistics(results)
        
        # Total expected: 5 + 10 + 20 + 8 = 43
        # Total owned: 5 + 3 + 0 + 6 = 14
        # Completion: 14/43 = 32.6%
        assert abs(stats.overall_completion_percentage - 32.6) < 0.1
    
    def test_most_incomplete_series(self, temp_collection):
        """Test getting most incomplete series"""
        self.create_test_collection(temp_collection)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        stats = calculate_statistics(results)
        
        incomplete = stats.get_most_incomplete_series(5)
        
        # Should have 3 series with issues
        assert len(incomplete) == 3
        
        # First should be "Incomplete Series" with 7 missing
        assert incomplete[0].series_name == "Incomplete Series"
        assert incomplete[0].missing_issues == 7
    
    def test_most_complete_series(self, temp_collection):
        """Test getting most complete (but not 100%) series"""
        self.create_test_collection(temp_collection)
        
        scanner = Mylar3Scanner(temp_collection)
        results = scanner.scan()
        stats = calculate_statistics(results)
        
        near_complete = stats.get_most_complete_series(5)
        
        # Should not include the complete series
        # Should have 2 incomplete series with issues
        assert len(near_complete) == 2
        
        # DC Series should be first (6/8 = 75%)
        assert near_complete[0].series_name == "DC Series"
        assert abs(near_complete[0].completion_percentage - 75.0) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
