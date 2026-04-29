"""
S3 client for storing and retrieving momentum screening data.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config as BotoConfig

from ..models import Stock

# Import config from the cfg module at project root
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from cfg.config import Config


logger = logging.getLogger(__name__)


class S3DataStorage:
    """Handles S3 operations for momentum screening data."""
    
    def __init__(self, bucket_name: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize S3 client with configuration.
        
        Args:
            bucket_name: S3 bucket name (defaults to config)
            region: AWS region (defaults to config)
        """
        self.bucket_name = bucket_name or Config.S3_BUCKET
        self.region = region or Config.AWS_REGION
        self.key_prefix = Config.S3_KEY_PREFIX
        
        # Configure boto3 with retry logic
        boto_config = BotoConfig(
            region_name=self.region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )
        
        try:
            self.s3_client = boto3.client('s3', config=boto_config)
            logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def _generate_s3_key(self, date_str: str) -> str:
        """Generate S3 key for momentum data file."""
        return f"{self.key_prefix}/momentum-data-{date_str}.json"
    
    def _validate_bucket_access(self) -> bool:
        """Validate S3 bucket access and permissions."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully validated access to bucket: {self.bucket_name}")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"Bucket {self.bucket_name} does not exist")
            elif error_code == '403':
                logger.error(f"Access denied to bucket {self.bucket_name}")
            else:
                logger.error(f"Error accessing bucket {self.bucket_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating bucket access: {e}")
            return False
    
    def upload_momentum_data(self, 
                           stock_data: Dict[str, Dict[str, List[Stock]]], 
                           market_date: str,
                           retry_count: int = 3) -> bool:
        """
        Upload processed momentum data to S3.
        
        Args:
            stock_data: Organized stock data by tier and timeframe
            market_date: Market date for the data (YYYY-MM-DD format)
            retry_count: Number of retry attempts
            
        Returns:
            True if upload successful, False otherwise
        """
        if not self._validate_bucket_access():
            return False
        
        # Serialize data to JSON format
        json_data = self._serialize_stock_data(stock_data, market_date)
        
        # Generate S3 key
        s3_key = self._generate_s3_key(market_date)
        
        # Upload with retry logic
        for attempt in range(retry_count):
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=json.dumps(json_data, indent=2),
                    ContentType='application/json',
                    ServerSideEncryption='AES256',
                    Metadata={
                        'generated_at': datetime.now(timezone.utc).isoformat(),
                        'market_date': market_date,
                        'data_version': '1.0'
                    }
                )
                
                logger.info(f"Successfully uploaded momentum data to s3://{self.bucket_name}/{s3_key}")
                return True
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                logger.warning(f"Upload attempt {attempt + 1} failed with error {error_code}: {e}")
                
                if attempt == retry_count - 1:
                    logger.error(f"Failed to upload after {retry_count} attempts")
                    return False
                    
            except Exception as e:
                logger.warning(f"Upload attempt {attempt + 1} failed with unexpected error: {e}")
                
                if attempt == retry_count - 1:
                    logger.error(f"Failed to upload after {retry_count} attempts")
                    return False
        
        return False
    
    def download_momentum_data(self, market_date: str) -> Optional[Dict[str, Any]]:
        """
        Download momentum data from S3.
        
        Args:
            market_date: Market date for the data (YYYY-MM-DD format)
            
        Returns:
            Deserialized momentum data or None if not found
        """
        s3_key = self._generate_s3_key(market_date)
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            json_data = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"Successfully downloaded momentum data from s3://{self.bucket_name}/{s3_key}")
            return json_data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"No momentum data found for date {market_date}")
            else:
                logger.error(f"Error downloading momentum data: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error downloading momentum data: {e}")
            return None
    
    def list_available_dates(self, limit: int = 30) -> List[str]:
        """
        List available momentum data dates in S3.
        
        Args:
            limit: Maximum number of dates to return
            
        Returns:
            List of available dates in YYYY-MM-DD format
        """
        try:
            # Fetch all objects (S3 returns alphabetically, not by date)
            # We must retrieve all keys then sort to find the most recent
            dates = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=f"{self.key_prefix}/momentum-data-"
            )
            for page in pages:
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    # Extract date from key: momentum-data/momentum-data-YYYY-MM-DD.json
                    if key.endswith('.json'):
                        date_part = key.split('-')[-3:]  # ['YYYY', 'MM', 'DD.json']
                        if len(date_part) == 3:
                            date_str = f"{date_part[0]}-{date_part[1]}-{date_part[2].replace('.json', '')}"
                            dates.append(date_str)

            dates.sort(reverse=True)  # Most recent first
            dates = dates[:limit]     # Trim to requested limit after sorting
            logger.info(f"Found {len(dates)} momentum data files in S3")
            return dates
            
        except Exception as e:
            logger.error(f"Error listing available dates: {e}")
            return []
    
    def _serialize_stock_data(self, 
                            stock_data: Dict[str, Dict[str, List[Stock]]], 
                            market_date: str) -> Dict[str, Any]:
        """
        Serialize stock data to JSON-compatible format.
        
        Args:
            stock_data: Organized stock data by tier and timeframe
            market_date: Market date for the data
            
        Returns:
            JSON-serializable dictionary
        """
        serialized_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_date": market_date,
            "data_version": "1.0",
            "tiers": {}
        }
        
        for tier, timeframe_data in stock_data.items():
            serialized_data["tiers"][tier] = {}
            
            for timeframe, stocks in timeframe_data.items():
                serialized_data["tiers"][tier][f"{timeframe}_day"] = [
                    self._serialize_stock(stock) for stock in stocks
                ]
        
        return serialized_data
    
    def _serialize_stock(self, stock: Stock) -> Dict[str, Any]:
        """
        Serialize a single Stock object to dictionary.
        
        Args:
            stock: Stock object to serialize
            
        Returns:
            Dictionary representation of stock
        """
        return {
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "current_price": stock.current_price,
            "market_cap": stock.market_cap,
            "momentum_7d": stock.momentum_7d,
            "momentum_30d": stock.momentum_30d,
            "momentum_60d": stock.momentum_60d,
            "momentum_90d": stock.momentum_90d,
            "ai_summary": stock.ai_summary,
            "tier": stock.get_tier()
        }
    
    def validate_json_schema(self, data: Dict[str, Any]) -> bool:
        """
        Validate JSON data against expected schema.
        
        Args:
            data: JSON data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["generated_at", "market_date", "data_version", "tiers"]
        
        # Check top-level fields
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate tiers structure
        if not isinstance(data["tiers"], dict):
            logger.error("Tiers field must be a dictionary")
            return False
        
        # Validate each tier
        expected_tiers = ["100B_200B", "200B_500B", "500B_1T", "1T_plus"]
        for tier in expected_tiers:
            if tier in data["tiers"]:
                if not self._validate_tier_data(data["tiers"][tier]):
                    return False
        
        logger.info("JSON schema validation passed")
        return True
    
    def _validate_tier_data(self, tier_data: Dict[str, Any]) -> bool:
        """Validate tier data structure."""
        expected_timeframes = ["7_day", "30_day", "60_day", "90_day"]
        
        for timeframe in expected_timeframes:
            if timeframe in tier_data:
                if not isinstance(tier_data[timeframe], list):
                    logger.error(f"Timeframe {timeframe} must be a list")
                    return False
                
                # Validate stock objects in the list
                for stock_data in tier_data[timeframe]:
                    if not self._validate_stock_data(stock_data):
                        return False
        
        return True
    
    def _validate_stock_data(self, stock_data: Dict[str, Any]) -> bool:
        """Validate individual stock data structure."""
        required_fields = ["ticker", "company_name", "current_price", "market_cap"]
        
        for field in required_fields:
            if field not in stock_data:
                logger.error(f"Missing required stock field: {field}")
                return False
        
        # Validate data types
        if not isinstance(stock_data["ticker"], str):
            logger.error("Ticker must be a string")
            return False
        
        if not isinstance(stock_data["current_price"], (int, float)):
            logger.error("Current price must be a number")
            return False
        
        if not isinstance(stock_data["market_cap"], int):
            logger.error("Market cap must be an integer")
            return False
        
        return True