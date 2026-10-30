export interface Dimensions{
    length: number;
    width: number;
    height: number;
}

export interface Item{
    dimensions: Dimensions;
    weight: number;
    quantity: number;
}

export interface CustomBoxRequest{
    item: Item;
    padding: number;
}

export interface CustomBoxResult{
    box_dimensions: Dimensions;
    volume: number;
    utilization: number;
}