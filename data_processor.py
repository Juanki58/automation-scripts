import math

def calculate_market_metrics(prices):
    """
    Analizes raw price data to calculate core market metrics.
    Demonstrates automation flow and data cleaning.
    """
    if not prices:
        return None
        
    # Clean data (ensure numbers only)
    clean_prices = [float(p) for p in prices if isinstance(p, (int, float))]
    
    total_days = len(clean_prices)
    if total_days == 0:
        return None
        
    # Calculate Average Price
    average_price = sum(clean_prices) / total_days
    
    # Calculate Volatility (Standard Deviation)
    variance = sum((x - average_price) ** 2 for x in clean_prices) / total_days
    volatility = math.sqrt(variance)
    
    return {
        "total_records": total_days,
        "average_price": round(average_price, 2),
        "volatility": round(volatility, 2),
        "highest_price": max(clean_prices),
        "lowest_price": min(clean_prices)
    }

# Example of local automation test
if __name__ == "__main__":
    # Simulated raw data feed from a market API
    raw_feed = [105.4, 106.2, 104.8, 107.5, 109.1, "error_string", 108.3]
    
    print("--- Starting Market Data Automation Clean ---")
    results = calculate_market_metrics(raw_feed)
    
    if results:
        print(f"Successfully processed {results['total_records']} market records.")
        print(f"Average Asset Price: ${results['average_price']}")
        print(f"Calculated Volatility (Risk Factor): {results['volatility']}")
        print(f"Highest Peak: ${results['highest_price']} | Lowest Drop: ${results['lowest_price']}")
    else:
        print("Data processing failed. Check feed structure.")
