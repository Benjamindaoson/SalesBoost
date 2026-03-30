"""Tests for ConversationAnalyzer (renamed from RLAIFPipeline) and RewardDataCollector stub."""
import pytest
from app.ai_core.rlaif.pipeline import ConversationAnalyzer, RewardDataCollector, RLAIFPipeline


def test_conversation_analyzer_is_rlaif_pipeline_alias():
    assert ConversationAnalyzer is RLAIFPipeline


def test_conversation_analyzer_instantiates():
    analyzer = ConversationAnalyzer(storage_dir="/tmp/test_rlaif")
    assert analyzer is not None


def test_conversation_analyzer_has_run_collection_cycle():
    assert hasattr(ConversationAnalyzer, "run_collection_cycle")


def test_conversation_analyzer_has_run_labeling_cycle():
    assert hasattr(ConversationAnalyzer, "run_labeling_cycle")


def test_reward_data_collector_stub_has_collect():
    assert hasattr(RewardDataCollector, "collect")


def test_reward_data_collector_stub_has_upload():
    assert hasattr(RewardDataCollector, "upload")


def test_reward_data_collector_collect_raises():
    collector = RewardDataCollector()
    with pytest.raises(NotImplementedError):
        collector.collect()


def test_reward_data_collector_upload_raises():
    collector = RewardDataCollector()
    with pytest.raises(NotImplementedError):
        collector.upload()
