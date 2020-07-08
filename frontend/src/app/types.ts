interface ColorInterface {
  red: number;
  green: number;
  blue: number;
  percentage: number;
  name: string | null;
  name_distance: number | null;
}


export class Color implements ColorInterface {
  red: number;
  green: number;
  blue: number;
  percentage: number;
  name: string | null;
  name_distance: number | null;

  constructor(data: ColorInterface) {
    this.red = data.red;
    this.green = data.green;
    this.blue = data.blue;
    this.percentage = data.percentage;
    this.name = data.name;
    this.name_distance = data.name_distance;
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
  origin: string
  url_big: string
  url_thumb: string
}


export interface ImageDetailResponseInterface {
  image: ImageDetailInterface
  colors: ColorInterface[]
}


export class ImageDetailResponse implements ImageDetailResponseInterface {

  image: ImageDetailInterface
  colors: Color[]

  constructor(data: ImageDetailResponseInterface) {
    this.image = data.image;
    this.colors = new Array<Color>();
    for (let index in data.colors)
      this.colors.push(new Color(data.colors[index]));
    this.colors.sort(
      (a: Color, b: Color) => b.percentage - a.percentage
    );
  }
}
