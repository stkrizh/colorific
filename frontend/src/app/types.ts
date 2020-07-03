interface ColorInterface {
  r: number;
  g: number;
  b: number;
  percentage: number;
}


export class Color implements ColorInterface {
  r: number;
  g: number;
  b: number;
  percentage: number;

  constructor(data: ColorInterface) {
    this.r = data.r;
    this.g = data.g;
    this.b = data.b;
    this.percentage = data.percentage;
  }

  toHex(): string {
    return `${this.r.toString(16).padStart(2, "0")}` +
      `${this.g.toString(16).padStart(2, "0")}` +
      `${this.b.toString(16).padStart(2, "0")}`
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
