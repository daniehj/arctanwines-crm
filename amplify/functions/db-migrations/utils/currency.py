"""
Currency utility functions for Arctan Wines CRM
Handles conversion between display format and Fiken's integer storage format

Fiken API uses integers for money:
- 336000 = 3,360.00 NOK
- 84000 = 840.00 NOK
- All amounts stored as øre/cents (smallest currency unit)
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Union, Optional

def nok_to_ore(amount: Union[float, Decimal, str]) -> int:
    """
    Convert NOK amount to øre (integer format for Fiken API)
    
    Args:
        amount: Amount in NOK (e.g., 3360.00)
    
    Returns:
        Amount in øre as integer (e.g., 336000)
    
    Examples:
        >>> nok_to_ore(3360.00)
        336000
        >>> nok_to_ore("840.50")
        84050
    """
    if amount is None:
        return 0
    
    # Convert to Decimal for precise calculation
    decimal_amount = Decimal(str(amount))
    
    # Multiply by 100 to convert to øre and round to nearest integer
    ore_amount = decimal_amount * 100
    
    # Round to nearest integer (handles floating point precision issues)
    return int(ore_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def ore_to_nok(ore_amount: Optional[int]) -> Decimal:
    """
    Convert øre amount to NOK (decimal format for display)
    
    Args:
        ore_amount: Amount in øre as integer (e.g., 336000)
    
    Returns:
        Amount in NOK as Decimal (e.g., 3360.00)
    
    Examples:
        >>> ore_to_nok(336000)
        Decimal('3360.00')
        >>> ore_to_nok(84050)
        Decimal('840.50')
    """
    if ore_amount is None:
        return Decimal('0.00')
    
    # Convert to Decimal and divide by 100
    nok_amount = Decimal(ore_amount) / 100
    
    # Quantize to 2 decimal places
    return nok_amount.quantize(Decimal('0.01'))

def eur_to_cents(amount: Union[float, Decimal, str]) -> int:
    """
    Convert EUR amount to cents (integer format)
    
    Args:
        amount: Amount in EUR (e.g., 25.50)
    
    Returns:
        Amount in cents as integer (e.g., 2550)
    """
    if amount is None:
        return 0
    
    decimal_amount = Decimal(str(amount))
    cents_amount = decimal_amount * 100
    return int(cents_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def cents_to_eur(cents_amount: Optional[int]) -> Decimal:
    """
    Convert cents amount to EUR (decimal format for display)
    
    Args:
        cents_amount: Amount in cents as integer (e.g., 2550)
    
    Returns:
        Amount in EUR as Decimal (e.g., 25.50)
    """
    if cents_amount is None:
        return Decimal('0.00')
    
    eur_amount = Decimal(cents_amount) / 100
    return eur_amount.quantize(Decimal('0.01'))

def format_nok(ore_amount: Optional[int]) -> str:
    """
    Format øre amount as NOK string for display
    
    Args:
        ore_amount: Amount in øre as integer
    
    Returns:
        Formatted string (e.g., "3,360.00 NOK")
    """
    if ore_amount is None:
        return "0.00 NOK"
    
    nok_amount = ore_to_nok(ore_amount)
    return f"{nok_amount:,.2f} NOK"

def format_eur(cents_amount: Optional[int]) -> str:
    """
    Format cents amount as EUR string for display
    
    Args:
        cents_amount: Amount in cents as integer
    
    Returns:
        Formatted string (e.g., "25.50 EUR")
    """
    if cents_amount is None:
        return "0.00 EUR"
    
    eur_amount = cents_to_eur(cents_amount)
    return f"{eur_amount:,.2f} EUR"

def calculate_margin_percentage(cost_ore: int, selling_price_ore: int) -> Decimal:
    """
    Calculate margin percentage between cost and selling price
    
    Args:
        cost_ore: Cost in øre
        selling_price_ore: Selling price in øre
    
    Returns:
        Margin percentage as Decimal
    
    Examples:
        >>> calculate_margin_percentage(84000, 336000)  # Cost 840 NOK, Sell 3360 NOK
        Decimal('75.00')  # 75% margin
    """
    if cost_ore == 0 or selling_price_ore == 0:
        return Decimal('0.00')
    
    cost = Decimal(cost_ore)
    selling_price = Decimal(selling_price_ore)
    
    margin = ((selling_price - cost) / selling_price) * 100
    return margin.quantize(Decimal('0.01'))

def calculate_markup_percentage(cost_ore: int, selling_price_ore: int) -> Decimal:
    """
    Calculate markup percentage over cost
    
    Args:
        cost_ore: Cost in øre
        selling_price_ore: Selling price in øre
    
    Returns:
        Markup percentage as Decimal
    
    Examples:
        >>> calculate_markup_percentage(84000, 336000)  # Cost 840 NOK, Sell 3360 NOK
        Decimal('300.00')  # 300% markup
    """
    if cost_ore == 0:
        return Decimal('0.00')
    
    cost = Decimal(cost_ore)
    selling_price = Decimal(selling_price_ore)
    
    markup = ((selling_price - cost) / cost) * 100
    return markup.quantize(Decimal('0.01')) 