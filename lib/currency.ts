/**
 * Currency utility functions for Arctan Wines CRM Frontend
 * Handles conversion between display format and Fiken's integer storage format
 * 
 * Fiken API uses integers for money:
 * - 336000 = 3,360.00 NOK
 * - 84000 = 840.00 NOK
 * - All amounts stored as øre/cents (smallest currency unit)
 */

/**
 * Format øre amount as NOK string for display
 * @param ore Amount in øre as integer
 * @returns Formatted string (e.g., "3,360.00 NOK")
 */
export const formatNOK = (ore: number | null | undefined): string => {
  if (ore === null || ore === undefined) {
    return "0.00 NOK";
  }
  return `${(ore / 100).toLocaleString('no-NO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} NOK`;
};

/**
 * Format cents amount as EUR string for display
 * @param cents Amount in cents as integer
 * @returns Formatted string (e.g., "€25.50")
 */
export const formatEUR = (cents: number | null | undefined): string => {
  if (cents === null || cents === undefined) {
    return "€0.00";
  }
  return `€${(cents / 100).toLocaleString('no-NO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

/**
 * Parse user input NOK to øre for storage
 * @param nokString NOK amount as string (e.g., "3360.50")
 * @returns Amount in øre as integer (e.g., 336050)
 */
export const parseNOKInput = (nokString: string): number => {
  if (!nokString || nokString.trim() === '') {
    return 0;
  }
  
  // Remove any NOK suffix and whitespace
  const cleanString = nokString.replace(/NOK/gi, '').replace(/\s/g, '');
  
  // Parse and convert to øre
  const nokAmount = parseFloat(cleanString);
  if (isNaN(nokAmount)) {
    return 0;
  }
  
  return Math.round(nokAmount * 100);
};

/**
 * Parse user input EUR to cents for storage
 * @param eurString EUR amount as string (e.g., "25.50")
 * @returns Amount in cents as integer (e.g., 2550)
 */
export const parseEURInput = (eurString: string): number => {
  if (!eurString || eurString.trim() === '') {
    return 0;
  }
  
  // Remove any EUR suffix, € symbol, and whitespace
  const cleanString = eurString.replace(/EUR/gi, '').replace(/€/g, '').replace(/\s/g, '');
  
  // Parse and convert to cents
  const eurAmount = parseFloat(cleanString);
  if (isNaN(eurAmount)) {
    return 0;
  }
  
  return Math.round(eurAmount * 100);
};

/**
 * Convert øre to NOK for display (without currency symbol)
 * @param ore Amount in øre as integer
 * @returns NOK amount as number
 */
export const oreToNOK = (ore: number | null | undefined): number => {
  if (ore === null || ore === undefined) {
    return 0;
  }
  return ore / 100;
};

/**
 * Convert cents to EUR for display (without currency symbol)
 * @param cents Amount in cents as integer
 * @returns EUR amount as number
 */
export const centsToEUR = (cents: number | null | undefined): number => {
  if (cents === null || cents === undefined) {
    return 0;
  }
  return cents / 100;
};

/**
 * Calculate margin percentage between cost and selling price
 * @param costOre Cost in øre
 * @param sellingPriceOre Selling price in øre
 * @returns Margin percentage as number
 */
export const calculateMarginPercentage = (costOre: number, sellingPriceOre: number): number => {
  if (costOre === 0 || sellingPriceOre === 0) {
    return 0;
  }
  
  return ((sellingPriceOre - costOre) / sellingPriceOre) * 100;
};

/**
 * Calculate markup percentage over cost
 * @param costOre Cost in øre
 * @param sellingPriceOre Selling price in øre
 * @returns Markup percentage as number
 */
export const calculateMarkupPercentage = (costOre: number, sellingPriceOre: number): number => {
  if (costOre === 0) {
    return 0;
  }
  
  return ((sellingPriceOre - costOre) / costOre) * 100;
};

/**
 * Convert EUR cents to NOK øre using exchange rate
 * @param eurCents Amount in EUR cents
 * @param exchangeRate EUR to NOK exchange rate
 * @returns Amount in NOK øre
 */
export const convertEURToNOKOre = (eurCents: number, exchangeRate: number): number => {
  const eurAmount = eurCents / 100;
  const nokAmount = eurAmount * exchangeRate;
  return Math.round(nokAmount * 100);
};

/**
 * Format amount with proper Norwegian number formatting
 * @param amount Number to format
 * @param decimals Number of decimal places (default: 2)
 * @returns Formatted string with Norwegian locale
 */
export const formatNumber = (amount: number | null | undefined, decimals: number = 2): string => {
  if (amount === null || amount === undefined) {
    return "0";
  }
  return amount.toLocaleString('no-NO', { 
    minimumFractionDigits: decimals, 
    maximumFractionDigits: decimals 
  });
};

/**
 * Validate if a string is a valid monetary amount
 * @param value String to validate
 * @returns True if valid monetary amount
 */
export const isValidMonetaryAmount = (value: string): boolean => {
  if (!value || value.trim() === '') {
    return false;
  }
  
  // Remove currency symbols and whitespace
  const cleanValue = value.replace(/[NOK€\s]/gi, '');
  
  // Check if it's a valid number
  const numValue = parseFloat(cleanValue);
  return !isNaN(numValue) && numValue >= 0;
};

/**
 * Currency input component helper - formats as user types
 * @param value Current input value
 * @param currency Currency type ('NOK' | 'EUR')
 * @returns Formatted value for display
 */
export const formatCurrencyInput = (value: string, currency: 'NOK' | 'EUR' = 'NOK'): string => {
  if (!value) return '';
  
  // Remove all non-numeric characters except decimal point
  const numericValue = value.replace(/[^\d.]/g, '');
  
  // Ensure only one decimal point
  const parts = numericValue.split('.');
  if (parts.length > 2) {
    return parts[0] + '.' + parts.slice(1).join('');
  }
  
  // Limit to 2 decimal places
  if (parts.length === 2 && parts[1].length > 2) {
    return parts[0] + '.' + parts[1].substring(0, 2);
  }
  
  return numericValue;
}; 