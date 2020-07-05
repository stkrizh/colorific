interface ColorInterface {
  red: number;
  green: number;
  blue: number;
  percentage: number;
}


export class Color implements ColorInterface {
  red: number;
  green: number;
  blue: number;
  percentage: number;

  constructor(data: ColorInterface) {
    this.red = data.red;
    this.green = data.green;
    this.blue = data.blue;
    this.percentage = data.percentage;
  }

  toHex(): string {
    return `${this.red.toString(16).padStart(2, "0")}` +
      `${this.green.toString(16).padStart(2, "0")}` +
      `${this.blue.toString(16).padStart(2, "0")}`
  }
}


interface ColorsResponseInterface {
  colors: Array<ColorInterface>;
}


export class ColorsResponse implements ColorsResponseInterface {
  colors = []

  constructor(data: Array<Color>) {
    this.colors = [];
    for (let index in data) {
      this.colors.push(new Color(data[index]));
    }
    this.colors.sort(
      (a: Color, b: Color) => b.percentage - a.percentage
    );
  }
}


interface ImageDetailInterface {
  id: string
  details_url: string
  regular_url: string
  small_url: string
  has_colors: boolean
}


export class ImageDetailResponse
  extends ColorsResponse
  implements ImageDetailInterface {

  id: string
  details_url: string
  regular_url: string
  small_url: string
  has_colors: boolean

  constructor(data: any) {
    super(data);
    this.id = data.id
    this.details_url = data.details_url
    this.regular_url = data.regular_url
    this.small_url = data.small_url
    this.has_colors = data.has_colors
  }
}
