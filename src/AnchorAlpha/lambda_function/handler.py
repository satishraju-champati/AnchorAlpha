"""
AWS Lambda function handler for AnchorAlpha momentum screener.

This module orchestrates the complete data processing pipeline:
1. Fetch large-cap stocks from FMP API
2. Calculate momentum across multiple timeframes
3. Generate AI summaries for top performers
4. Store results in S3

Requirements: 5.2, 6.1, 8.1, 8.3
"""

import json
import logging
import os
import time
import traceback
from datetime import datetime, date, timezone
from typing import Dict, List, Optional, Any

from ..api.fmp_client import FMPClient, FMPAPIError
from ..api.perplexity_client import PerplexityClient, PerplexityAPIError
from ..api.perplexity_factory import PerplexityFactory
from ..momentum_engine import MomentumEngine, HistoricalPriceData
from ..storage.data_pipeline import MomentumDataPipeline
from ..models import Stock
from ..utils.logging_utils import StructuredLogger, CloudWatchMetricsPublisher, SNSNotificationManager
from ..utils.api_monitoring import get_api_monitor
from cfg.config import Config


class LambdaOrchestrator:
    """Main orchestrator for the Lambda function pipeline."""
    
    def __init__(self):
        """Initialize the orchestrator with required components."""
        self.execution_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.market_date = date.today().strftime("%Y-%m-%d")
        
        # Initialize enhanced logging and monitoring
        self.logger = StructuredLogger("LambdaOrchestrator", self.execution_id)
        self.api_monitor = get_api_monitor()
        self.metrics_publisher = CloudWatchMetricsPublisher()
        self.notification_manager = SNSNotificationManager()
        
        # Initialize components
        self.fmp_client = None
        self.perplexity_client = None
        self.momentum_engine = MomentumEngine()
        self.data_pipeline = MomentumDataPipeline()
    
    def _initialize_clients(self) -> bool:
        """Initialize API clients with error handling."""
        try:
            # Initialize FMP client
            fmp_api_key = os.getenv("FMP_API_KEY")
            if not fmp_api_key:
                raise ValueError("FMP_API_KEY environment variable is required")
            
            self.fmp_client = FMPClient(fmp_api_key)
            self.logger.info("FMP client initialized successfully")
            
            # Initialize Perplexity client
            perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
            if not perplexity_api_key:
                self.logger.warning("PERPLEXITY_API_KEY not found, using mock client")
                self.perplexity_client = PerplexityFactory.create_client(use_mock=True)
            else:
                self.perplexity_client = PerplexityFactory.create_client(
                    api_key=perplexity_api_key, 
                    use_mock=False
                )
            
            self.logger.info("Perplexity client initialized successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize API clients: {str(e)}"
            self.logger.error(error_msg, exception=e)
            return False
    
    def _fetch_stock_data(self) -> List[Stock]:
        """Fetch large-cap stock data from FMP API."""
        try:
            self.logger.info("Starting stock data fetch from FMP API")
            
            # Check rate limits before making request
            wait_time = self.api_monitor.check_rate_limit("FMP")
            if wait_time > 0:
                self.logger.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            
            # Get large-cap stocks using screener with API monitoring
            with self.logger.api_call_timer("FMP", "stock-screener"):
                screener_data = self.fmp_client.get_large_cap_stocks()
            
            self.logger.log_processing_metrics("stock_fetch", stocks_fetched=len(screener_data))
            
            # Convert to Stock objects
            stocks = []
            for stock_data in screener_data:
                stock = self.fmp_client.create_stock_from_screener_data(stock_data)
                if stock:
                    stocks.append(stock)
            
            self.logger.info(
                f"Created {len(stocks)} valid Stock objects",
                valid_stocks=len(stocks),
                filtered_out=len(screener_data) - len(stocks)
            )
            
            return stocks
            
        except FMPAPIError as e:
            error_msg = f"FMP API error during stock fetch: {str(e)}"
            self.logger.error(error_msg, exception=e)
            raise
        except Exception as e:
            error_msg = f"Unexpected error during stock fetch: {str(e)}"
            self.logger.error(error_msg, exception=e)
            raise
    
    def _fetch_historical_data_batch(self, stocks: List[Stock]) -> Dict[str, HistoricalPriceData]:
        """Fetch historical price data for a batch of stocks."""
        historical_data = {}
        failed_fetches = 0
        
        self.logger.info(f"Starting historical data fetch for {len(stocks)} stocks")
        
        for i, stock in enumerate(stocks):
            try:
                # Check rate limits
                wait_time = self.api_monitor.check_rate_limit("FMP")
                if wait_time > 0:
                    time.sleep(wait_time)
                
                # Fetch historical prices with monitoring
                with self.logger.api_call_timer("FMP", f"historical-price-full/{stock.ticker}"):
                    price_data = self.fmp_client.get_historical_prices(stock.ticker, days=100)
                
                if "historical" not in price_data or not price_data["historical"]:
                    self.logger.warning(f"No historical data for {stock.ticker}", ticker=stock.ticker)
                    failed_fetches += 1
                    continue
                
                # Extract prices for specific days ago
                historical_prices = price_data["historical"]
                historical_prices.sort(key=lambda x: x["date"], reverse=True)  # Most recent first
                
                # Create HistoricalPriceData object
                hist_data = HistoricalPriceData(
                    ticker=stock.ticker,
                    current_price=stock.current_price
                )
                
                # Extract prices for momentum calculation windows
                if len(historical_prices) > 7:
                    hist_data.prices_7d_ago = historical_prices[7]["close"]
                if len(historical_prices) > 30:
                    hist_data.prices_30d_ago = historical_prices[30]["close"]
                if len(historical_prices) > 60:
                    hist_data.prices_60d_ago = historical_prices[60]["close"]
                if len(historical_prices) > 90:
                    hist_data.prices_90d_ago = historical_prices[90]["close"]
                
                historical_data[stock.ticker] = hist_data
                
                # Log progress every 50 stocks
                if (i + 1) % 50 == 0:
                    self.logger.info(f"Historical data progress: {i + 1}/{len(stocks)} stocks processed")
                
            except Exception as e:
                error_msg = f"Failed to fetch historical data for {stock.ticker}: {str(e)}"
                self.logger.warning(error_msg, ticker=stock.ticker)
                failed_fetches += 1
                continue
        
        success_rate = (len(historical_data) / len(stocks)) * 100 if stocks else 0
        self.logger.info(
            "Historical data fetch completed",
            successful_fetches=len(historical_data),
            failed_fetches=failed_fetches,
            success_rate=f"{success_rate:.1f}%"
        )
        
        return historical_data
    
    def _calculate_momentum_for_stocks(self, stocks: List[Stock], historical_data: Dict[str, HistoricalPriceData]) -> List[Stock]:
        """Calculate momentum for all stocks with historical data."""
        try:
            self.logger.info("Starting momentum calculations")
            
            # Prepare data for batch processing
            stock_batch_data = []
            for stock in stocks:
                if stock.ticker in historical_data:
                    stock_batch_data.append((
                        stock.ticker,
                        stock.company_name,
                        stock.current_price,
                        stock.market_cap,
                        historical_data[stock.ticker]
                    ))
            
            # Process momentum calculations
            processed_stocks = self.momentum_engine.process_stock_batch(stock_batch_data)
            
            # Validate momentum data
            validation_stats = self.momentum_engine.validate_momentum_data(processed_stocks)
            
            self.logger.log_processing_metrics("momentum_calculation", stocks_processed=len(processed_stocks))
            self.logger.info(
                "Momentum calculations completed",
                processed_stocks=len(processed_stocks),
                validation_stats=validation_stats
            )
            
            return processed_stocks
            
        except Exception as e:
            error_msg = f"Error during momentum calculations: {str(e)}"
            self.logger.error(error_msg, exception=e)
            raise
    
    def _generate_ai_summaries(self, tier_rankings: Dict[str, Dict[int, List[Stock]]]) -> Dict[str, Dict[int, List[Stock]]]:
        """Generate AI summaries for top performing stocks."""
        try:
            self.logger.info("Starting AI summary generation")
            
            # Collect all top performers across tiers and timeframes
            top_performers = []
            for tier, timeframe_data in tier_rankings.items():
                for timeframe, stocks in timeframe_data.items():
                    # Take top 5 from each tier/timeframe for AI summaries
                    top_performers.extend(stocks[:5])
            
            # Remove duplicates (same stock might be top performer in multiple timeframes)
            unique_performers = {}
            for stock in top_performers:
                if stock.ticker not in unique_performers:
                    unique_performers[stock.ticker] = stock
            
            self.logger.info(f"Generating summaries for {len(unique_performers)} unique top performers")
            
            # Prepare data for batch summary generation
            stocks_for_summaries = []
            for stock in unique_performers.values():
                momentum_data = {
                    "7d": stock.momentum_7d,
                    "30d": stock.momentum_30d,
                    "60d": stock.momentum_60d,
                    "90d": stock.momentum_90d
                }
                
                stocks_for_summaries.append({
                    "ticker": stock.ticker,
                    "company_name": stock.company_name,
                    "momentum_data": momentum_data
                })
            
            # Generate summaries with rate limiting and monitoring
            summaries = {}
            for stock_info in stocks_for_summaries:
                ticker = stock_info["ticker"]
                
                # Check rate limits
                wait_time = self.api_monitor.check_rate_limit("Perplexity")
                if wait_time > 0:
                    time.sleep(wait_time)
                
                try:
                    with self.logger.api_call_timer("Perplexity", "chat/completions"):
                        summary = self.perplexity_client.generate_stock_summary(
                            ticker,
                            stock_info["company_name"],
                            stock_info["momentum_data"]
                        )
                    summaries[ticker] = summary
                    
                except Exception as e:
                    self.logger.warning(f"Failed to generate summary for {ticker}", exception=e)
                    summaries[ticker] = f"Summary for {stock_info['company_name']} is currently unavailable."
            
            # Apply summaries to stocks in tier rankings
            for tier, timeframe_data in tier_rankings.items():
                for timeframe, stocks in timeframe_data.items():
                    for stock in stocks:
                        if stock.ticker in summaries:
                            stock.ai_summary = summaries[stock.ticker]
            
            self.logger.log_processing_metrics("ai_summary_generation", summaries_generated=len(summaries))
            self.logger.info(f"AI summary generation completed", summaries_generated=len(summaries))
            
            return tier_rankings
            
        except PerplexityAPIError as e:
            error_msg = f"Perplexity API error during summary generation: {str(e)}"
            self.logger.warning(error_msg, exception=e)
            # Continue without summaries
            return tier_rankings
        except Exception as e:
            error_msg = f"Unexpected error during AI summary generation: {str(e)}"
            self.logger.warning(error_msg, exception=e)
            # Continue without summaries
            return tier_rankings
    
    def _store_results(self, processed_stocks: List[Stock]) -> bool:
        """Store processed results in S3."""
        try:
            self.logger.info("Starting S3 data storage")
            
            success = self.data_pipeline.process_and_store_momentum_data(
                processed_stocks, 
                self.market_date
            )
            
            # Log S3 operation
            bucket = os.getenv("S3_BUCKET", "anchoralpha-data")
            key = f"momentum-data/{self.market_date}/processed_data.json"
            self.logger.log_s3_operation("upload", bucket, key, success)
            
            if success:
                self.logger.info("S3 data storage completed successfully")
                return True
            else:
                error_msg = "S3 data storage failed"
                self.logger.error(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Error during S3 storage: {str(e)}"
            self.logger.error(error_msg, exception=e)
            return False
    
    def execute_pipeline(self) -> Dict[str, Any]:
        """Execute the complete momentum screening pipeline."""
        try:
            self.logger.info("Starting AnchorAlpha momentum screening pipeline")
            
            # Step 1: Initialize API clients
            if not self._initialize_clients():
                raise Exception("Failed to initialize API clients")
            
            # Step 2: Fetch stock data
            stocks = self._fetch_stock_data()
            if not stocks:
                raise Exception("No stocks fetched from FMP API")
            
            # Step 3: Fetch historical price data
            historical_data = self._fetch_historical_data_batch(stocks)
            if not historical_data:
                raise Exception("No historical data fetched")
            
            # Step 4: Calculate momentum
            processed_stocks = self._calculate_momentum_for_stocks(stocks, historical_data)
            if not processed_stocks:
                raise Exception("No stocks processed for momentum")
            
            # Step 5: Generate tier rankings
            tier_rankings = self.momentum_engine.get_comprehensive_rankings(processed_stocks)
            
            # Step 6: Generate AI summaries
            tier_rankings_with_summaries = self._generate_ai_summaries(tier_rankings)
            
            # Step 7: Store results in S3
            storage_success = self._store_results(processed_stocks)
            
            # Step 8: Publish metrics and generate reports
            self._publish_final_metrics()
            
            # Finalize execution
            metrics = self.logger.get_metrics()
            metrics.success = storage_success and len(metrics.errors) == 0
            
            self.logger.finalize_and_log_metrics()
            
            # Send notifications if there were critical errors
            if not metrics.success:
                self.notification_manager.send_critical_error_notification(
                    "Pipeline execution failed with errors",
                    self.execution_id,
                    metrics
                )
            
            return {
                "statusCode": 200 if metrics.success else 500,
                "body": json.dumps({
                    "message": "Pipeline execution completed",
                    "execution_id": self.execution_id,
                    "success": metrics.success,
                    "summary": {
                        "stocks_fetched": metrics.stocks_fetched,
                        "stocks_processed": metrics.stocks_processed,
                        "summaries_generated": metrics.summaries_generated,
                        "duration_seconds": metrics.duration_seconds,
                        "error_count": len(metrics.errors),
                        "warning_count": len(metrics.warnings)
                    }
                })
            }
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {str(e)}"
            metrics = self.logger.get_metrics()
            metrics.add_error(error_msg)
            metrics.finalize()
            
            self.logger.error(error_msg, exception=e)
            self.logger.finalize_and_log_metrics()
            
            # Send critical error notification
            self.notification_manager.send_critical_error_notification(
                error_msg,
                self.execution_id,
                metrics
            )
            
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "message": "Pipeline execution failed",
                    "error": error_msg,
                    "execution_id": self.execution_id
                })
            }
    
    def _publish_final_metrics(self):
        """Publish final metrics and generate usage reports."""
        try:
            # Publish execution metrics to CloudWatch
            metrics = self.logger.get_metrics()
            self.metrics_publisher.publish_execution_metrics(metrics)
            
            # Publish API usage metrics
            self.api_monitor.publish_metrics_to_cloudwatch()
            
            # Save usage report to S3
            bucket = os.getenv("S3_BUCKET", "anchoralpha-data")
            self.api_monitor.save_usage_report_to_s3(bucket)
            
            # Publish rate limit utilization metrics
            rate_limit_status = self.api_monitor.get_rate_limit_status()
            for api_name, status in rate_limit_status.items():
                if api_name == "FMP":
                    self.metrics_publisher.publish_api_rate_limit_metrics(
                        api_name, status["requests_in_last_minute"], 300
                    )
                elif api_name == "Perplexity":
                    self.metrics_publisher.publish_api_rate_limit_metrics(
                        api_name, status["requests_in_last_minute"], 60
                    )
            
            self.logger.info("Final metrics and reports published successfully")
            
        except Exception as e:
            self.logger.error("Failed to publish final metrics", exception=e)


def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    
    This is the main entry point for the Lambda function that orchestrates
    the complete AnchorAlpha momentum screening pipeline.
    
    Args:
        event: Lambda event data (from EventBridge trigger)
        context: Lambda runtime context
        
    Returns:
        Dictionary with statusCode and body for Lambda response
    """
    # Initialize structured logger for the handler
    execution_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    handler_logger = StructuredLogger("LambdaHandler", execution_id)
    
    # Log the incoming event
    handler_logger.info(
        "Lambda function invoked",
        event=event,
        context_info={
            "function_name": context.function_name,
            "function_version": context.function_version,
            "invoked_function_arn": context.invoked_function_arn,
            "memory_limit_in_mb": context.memory_limit_in_mb,
            "remaining_time_in_millis": context.get_remaining_time_in_millis()
        }
    )
    
    try:
        # Create and execute the orchestrator
        orchestrator = LambdaOrchestrator()
        result = orchestrator.execute_pipeline()
        
        # Log final result
        handler_logger.info(
            "Lambda function completed",
            result=result,
            remaining_time_in_millis=context.get_remaining_time_in_millis()
        )
        
        return result
        
    except Exception as e:
        error_response = {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Lambda function failed",
                "error": str(e),
                "execution_id": execution_id,
                "traceback": traceback.format_exc()
            })
        }
        
        handler_logger.error(
            "Lambda function failed with unhandled exception",
            exception=e,
            response=error_response
        )
        
        return error_response