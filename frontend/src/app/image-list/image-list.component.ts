import { Component, Input, OnChanges, OnInit, SimpleChange } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { ActivatedRoute } from "@angular/router";
import { StateService } from "../state.service";


interface Image {
  id: string
  origin: string
  url_big: string;
  url_thumb: string;
}


@Component({
  selector: "app-image-list",
  templateUrl: "./image-list.component.html",
  styleUrls: ["./image-list.component.scss"]
})
export class ImageListComponent implements OnInit, OnChanges {
  @Input() color: string | null;
  images: Image[] = [];

  constructor(
    private http: HttpClient,
    private route: ActivatedRoute,
    private state: StateService
  ) {}

  ngOnInit() {
    this.route.paramMap.subscribe(params => {
      let routerColor = params.get("color");
      if (routerColor !== null) {
        this.color = routerColor;
        this.fetchImages();
      }
    })
  }

  ngOnChanges(changes: {[propKey: string]: SimpleChange}) {
    if ("color" in changes)
      this.fetchImages();
  }

  fetchImages() {
    this.state.showLoaderOverlay();
    const url = `http://localhost:8080/images?color=${this.color}`;
    this.http.get(url).subscribe(
      (response) => {
        this.state.turnOffLoaderOverlay();
        const imagesResponse = <Image[]>response;
        this.images = imagesResponse;
      },
      (error) => {
        this.state.turnOffLoaderOverlay();
        console.log(error);
      }
    );
  }

  showImageDetail(imageID: string) {
    this.state.showImageDetail(imageID);
  }
}
